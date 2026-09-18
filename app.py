"""MedSyn Streamlit research workstation.

The app is intentionally an integration layer: domain modules are imported
when available and small, clearly marked fallbacks keep the frontend usable
while the parallel modules are under development.
"""

from __future__ import annotations

import io
import importlib
import json
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="MedSyn | Synthetic Cohort Workstation",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = {
    "navy": "#16324F",
    "blue": "#2E6F95",
    "slate": "#5C6B73",
    "line": "#D9E2E8",
    "pale": "#F4F7F9",
    "green": "#2F6B58",
    "amber": "#A66A1F",
    "red": "#9C3D3D",
}

STEPS = [
    ("Upload", "Load source data"),
    ("Profile", "Inspect source"),
    ("Cohort", "Design population"),
    ("Feasibility", "Review evidence"),
    ("Generation", "Create cohort"),
    ("Sanity", "Mechanical checks"),
    ("Why trust this?", "Research report"),
    ("Export", "Download results"),
]


def _init_state() -> None:
    defaults = {
        "uploaded_df": None,
        "profile_output": None,
        "sparsity_output": None,
        "cohort_request": None,
        "feasibility_output": None,
        "generated_df": None,
        "sanity_output": None,
        "validation_output": None,
        "shift_output": None,
        "longitudinal_df": None,
        "current_step": 0,
        "selected_generation_model": "gaussian_copula",
        "sparse_confirmed": False,
        "sparse_confirmation": False,
        "demo_loaded": False,
        "generation_complete": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _style() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: #fbfcfd; color: {PALETTE["navy"]}; }}
        [data-testid="stSidebar"] {{ background: {PALETTE["pale"]}; border-right: 1px solid {PALETTE["line"]}; }}
        .research-banner {{ border: 1px solid #E4C98A; background: #FFF8E8; color: #684D1E;
            padding: .65rem .9rem; margin-bottom: 1.1rem; font-size: .88rem; }}
        .metric-card {{ background: white; border: 1px solid {PALETTE["line"]}; padding: .85rem 1rem; min-height: 92px; }}
        .metric-label {{ color: {PALETTE["slate"]}; font-size: .76rem; text-transform: uppercase; letter-spacing: .06em; }}
        .metric-value {{ color: {PALETTE["navy"]}; font: 600 1.45rem ui-monospace, SFMono-Regular, Menlo, monospace; margin-top: .35rem; }}
        .section-kicker {{ color: {PALETTE["blue"]}; font: 600 .74rem ui-monospace, SFMono-Regular, Menlo, monospace;
            letter-spacing: .11em; text-transform: uppercase; }}
        .evidence {{ border-left: 3px solid {PALETTE["blue"]}; background: white; padding: .8rem 1rem; border-top: 1px solid {PALETTE["line"]};
            border-right: 1px solid {PALETTE["line"]}; border-bottom: 1px solid {PALETTE["line"]}; }}
        h1, h2, h3 {{ letter-spacing: -.02em; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _banner() -> None:
    st.markdown(
        '<div class="research-banner"><strong>For research and testing purposes only.</strong> '
        "Not clinically validated.</div>",
        unsafe_allow_html=True,
    )


def _metric(label: str, value: Any) -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def _import_optional(module_name: str) -> Optional[Any]:
    try:
        return importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError):
        return None


def _call_first(module_names: Sequence[str], function_names: Sequence[str], *args: Any, **kwargs: Any) -> Any:
    for module_name in module_names:
        module = _import_optional(module_name)
        if module is None:
            continue
        for function_name in function_names:
            function = getattr(module, function_name, None)
            if function is None:
                continue
            try:
                return function(*args, **kwargs)
            except TypeError:
                continue
    return None


def _frontend_mock_demo() -> pd.DataFrame:
    """Development-only demo source; removed automatically when a demo CSV exists."""
    rng = np.random.default_rng(405)
    rows = []
    for patient_id in range(500):
        age = int(rng.integers(35, 86))
        diabetic = int(rng.random() < 0.32)
        adherence = int(rng.integers(35, 96))
        if patient_id < 2:
            age, diabetic, adherence = 72, 1, 25
        else:
            # Keep the demo's requested three-way intersection intentionally
            # sparse without embedding its counts in the UI.
            if diabetic and age > 65:
                age = 60
            if adherence < 40:
                adherence = 60
        for month in range(6):
            rows.append(
                {
                    "patient_id": f"P{patient_id:04d}",
                    "month": month,
                    "age": age,
                    "diabetic": diabetic,
                    "systolic_bp": int(np.clip(rng.normal(128 + diabetic * 8, 12), 90, 210)),
                    "activity_steps": int(np.clip(rng.normal(7000, 1800), 300, 18000)),
                    "medication_adherence_pct": int(np.clip(adherence + rng.normal(0, 4), 0, 100)),
                    "pain_score": int(np.clip(rng.normal(3 + diabetic, 2), 0, 10)),
                }
            )
    return pd.DataFrame(rows)


def _load_demo() -> pd.DataFrame:
    for path in ("data/demo_patients.csv", "demo_patients.csv"):
        try:
            return pd.read_csv(path)
        except FileNotFoundError:
            continue
    st.info("Demo CSV is not present in this checkout; using an isolated frontend development fixture.")
    return _frontend_mock_demo()


def _read_upload(uploaded_file: Any) -> pd.DataFrame:
    suffix = uploaded_file.name.lower().rsplit(".", 1)[-1]
    if suffix == "csv":
        return pd.read_csv(uploaded_file)
    if suffix in {"xlsx", "xls"}:
        return pd.read_excel(uploaded_file)
    raise ValueError("Please upload a CSV or XLSX file.")


def _source_summary(data: pd.DataFrame) -> Dict[str, Any]:
    patient_col = next((c for c in data.columns if "patient" in c.lower() and "id" in c.lower()), None)
    time_col = next(
        (c for c in data.columns if any(token in c.lower() for token in ("month", "date", "time", "timestamp"))),
        None,
    )
    missing = int(data.isna().sum().sum())
    return {
        "rows": len(data),
        "patients": data[patient_col].nunique() if patient_col else len(data),
        "columns": len(data.columns),
        "missing": missing,
        "missing_pct": round(missing / max(data.size, 1) * 100, 2),
        "time_col": time_col,
        "temporal_coverage": (
            f"{data[time_col].min()} → {data[time_col].max()}" if time_col else "Not detected"
        ),
    }


def _profile_source(data: pd.DataFrame) -> Dict[str, Any]:
    profile = _call_first(
        ("backend.profiling.data_ingest", "backend.data_ingest", "data_ingest"),
        ("profile_dataset", "profile_data", "infer_profile"),
        data,
    )
    if profile is not None:
        return profile if isinstance(profile, Mapping) else {"result": profile}
    numeric = data.select_dtypes(include=np.number)
    stats = numeric.describe().T.reset_index().rename(columns={"index": "variable"})
    return {"statistics": stats, "dtypes": data.dtypes.astype(str).to_dict(), "development_fallback": True}


def _sparsity_source(data: pd.DataFrame) -> Any:
    result = _call_first(
        ("backend.profiling.sparsity", "backend.sparsity", "sparsity"),
        ("analyze_sparsity", "profile_sparsity", "calculate_sparsity"),
        data,
    )
    if result is not None:
        return result
    return {"missing_cells": int(data.isna().sum().sum()), "development_fallback": True}


def _condition_frame(request: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for condition in request.get("conditions", []):
        rows.append(
            {
                "Variable": condition.get("variable"),
                "Operator": condition.get("operator"),
                "Value": condition.get("value"),
                "Target %": condition.get("target_pct"),
            }
        )
    return pd.DataFrame(rows)


def _mock_feasibility(data: pd.DataFrame, request: Mapping[str, Any]) -> Dict[str, Any]:
    """Frontend-only evidence fallback; the feasibility module owns real decisions."""
    patient_col = next(
        (column for column in data.columns if "patient" in column.lower() and "id" in column.lower()),
        None,
    )
    denominator = data[patient_col].nunique() if patient_col else len(data)

    def cohort_count(mask: pd.Series) -> int:
        return int(data.loc[mask, patient_col].nunique()) if patient_col else int(mask.sum())

    condition_rows = []
    masks = []
    for condition in request.get("conditions", []):
        variable = condition["variable"]
        if variable not in data.columns:
            count = 0
            mask = pd.Series(False, index=data.index)
        else:
            value, operator = condition["value"], condition["operator"]
            mask = {
                "==": data[variable] == value,
                ">": data[variable] > value,
                ">=": data[variable] >= value,
                "<": data[variable] < value,
                "<=": data[variable] <= value,
                "!=": data[variable] != value,
            }.get(operator, pd.Series(False, index=data.index))
            count = cohort_count(mask)
        masks.append(mask)
        condition_rows.append(
            {
                "variable": variable,
                "target_pct": condition["target_pct"],
                "source_count": count,
                "source_pct": round(count / max(denominator, 1) * 100, 2),
                "status": "Sparse" if count < 10 else "Moderate",
            }
        )
    combination = cohort_count(np.logical_and.reduce(masks)) if masks else denominator
    return {
        "overall": "Sparse" if combination < 10 else "Moderate",
        "conditions": condition_rows,
        "combination": {"order": len(masks), "source_count": combination, "source_pct": round(combination / max(denominator, 1) * 100, 2)},
        "development_fallback": True,
    }


def _check_feasibility(data: pd.DataFrame, request: Mapping[str, Any]) -> Dict[str, Any]:
    result = _call_first(
        ("backend.feasibility", "feasibility"),
        ("check_feasibility", "evaluate_feasibility", "assess_feasibility"),
        data,
        request,
    )
    if isinstance(result, Mapping):
        return dict(result)
    return _mock_feasibility(data, request)


def _generate(data: pd.DataFrame, request: Mapping[str, Any], model: str) -> pd.DataFrame:
    generation = _import_optional("backend.generation")
    if generation is None:
        return _frontend_mock_generation(data, request, model)
    function = getattr(generation, "generate_cross_sectional", None)
    if function is None:
        return _frontend_mock_generation(data, request, model)
    return function(data, request, int(request["target_n"]), model=model)


def _frontend_mock_generation(
    data: pd.DataFrame, request: Mapping[str, Any], model: str
) -> pd.DataFrame:
    """Development-only pass-through fixture until Agent 3 is available."""
    if model not in {"gaussian_copula", "ctgan"}:
        raise ValueError(f"Unsupported generation model: {model}")
    result = data.sample(
        n=int(request["target_n"]), replace=True, random_state=405
    ).reset_index(drop=True)
    result.attrs["actual_proportions"] = {
        condition["variable"]: round(
            float(
                {
                    "==": result[condition["variable"]] == condition["value"],
                    ">": result[condition["variable"]] > condition["value"],
                    "<": result[condition["variable"]] < condition["value"],
                }.get(condition["operator"], pd.Series(False, index=result.index)).mean()
                * 100
            ),
            2,
        )
        for condition in request.get("conditions", [])
        if condition["variable"] in result.columns
    }
    result.attrs["development_fallback"] = True
    return result


def _sanity(data: pd.DataFrame, generated: pd.DataFrame) -> Any:
    module = _import_optional("sanity")
    function = getattr(module, "run_sanity_checks", None) if module else None
    if function:
        schema = {
            "numeric_cols": list(data.select_dtypes(include=np.number).columns),
        }
        return function(generated, schema, data)
    checks = []
    for column in generated.columns:
        checks.append(
            {
                "check": f"{column}: missingness",
                "status": "PASS" if not generated[column].isna().any() else "WARN",
                "detail": f"{int(generated[column].isna().sum())} missing values",
            }
        )
    return {"checks": checks, "development_fallback": True}


def _validation(source: pd.DataFrame, generated: pd.DataFrame) -> Any:
    module = _import_optional("validation")
    if module is None:
        return {"status": "Unavailable", "development_fallback": True}
    result: Dict[str, Any] = {}
    for function_name, result_key, args in (
        ("compute_quality_metrics", "quality", (source, generated)),
        ("compute_privacy_metrics", "privacy", (source, generated)),
        ("compute_missingness_similarity", "missingness", (source, generated)),
    ):
        function = getattr(module, function_name, None)
        result[result_key] = (
            function(*args) if function else {"status": "Unavailable"}
        )
    tstr = getattr(module, "compute_tstr", None)
    if tstr:
        target = next(
            (column for column in ("diabetic", "pain_score", "systolic_bp") if column in source),
            None,
        )
        result["tstr"] = tstr(source, generated, target) if target else {"status": "Unavailable"}
    return result


def _actual_proportions(generated: pd.DataFrame, request: Mapping[str, Any]) -> pd.DataFrame:
    shift = _import_optional("shift")
    actual = getattr(shift, "actual_proportions", None) if shift else None
    if actual:
        return actual(generated, request)
    rows = []
    for condition in request.get("conditions", []):
        variable = condition["variable"]
        if variable not in generated.columns:
            actual = None
        else:
            operator = condition["operator"]
            value = condition["value"]
            mask = {
                "==": generated[variable] == value,
                ">": generated[variable] > value,
                ">=": generated[variable] >= value,
                "<": generated[variable] < value,
                "<=": generated[variable] <= value,
                "!=": generated[variable] != value,
            }.get(operator, pd.Series(False, index=generated.index))
            actual = round(float(mask.mean() * 100), 2)
        rows.append({"Variable": variable, "Source target %": condition["target_pct"], "Generated %": actual})
    return pd.DataFrame(rows)


def _population_shift(
    source: pd.DataFrame,
    request: Mapping[str, Any],
    generated: Optional[pd.DataFrame] = None,
) -> Optional[pd.DataFrame]:
    module = _import_optional("shift")
    function = getattr(module, "compute_population_shift", None) if module else None
    if function is None:
        return _actual_proportions(generated, request) if generated is not None else None
    result = function(source, request, generated_df=generated)
    formatter = getattr(module, "format_population_shift_table", None)
    return formatter(result) if formatter else result.to_dataframe()


def _condition_evidence_table(result: Mapping[str, Any]) -> pd.DataFrame:
    rows = list(result.get("conditions", []))
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame()


def _quality_relationship_table(validation: Mapping[str, Any]) -> pd.DataFrame:
    quality = validation.get("quality", {}) if isinstance(validation, Mapping) else {}
    correlations = quality.get("correlations", {}) if isinstance(quality, Mapping) else {}
    rows = []
    for relationship, values in correlations.items():
        if not isinstance(values, Mapping):
            continue
        rows.append(
            {
                "Relationship": relationship,
                "Source": values.get("source_correlation"),
                "Synthetic": values.get("synthetic_correlation"),
                "Difference": values.get("difference"),
            }
        )
    return pd.DataFrame(rows)


def _metric_from_mapping(data: Any, keys: Iterable[str], default: str = "Unavailable") -> Any:
    if isinstance(data, Mapping):
        for key in keys:
            if key in data and not isinstance(data[key], (dict, list, tuple)):
                return data[key]
    return default


def _correlation_chart(source: pd.DataFrame, generated: pd.DataFrame, columns: Sequence[str]) -> go.Figure:
    source_corr = source.select_dtypes(include=np.number).corr()
    generated_corr = generated.select_dtypes(include=np.number).corr()
    columns = [c for c in columns if c in source_corr and c in generated_corr]
    fig = go.Figure()
    if columns:
        fig = make_subplots_correlation(source_corr.loc[columns, columns], generated_corr.loc[columns, columns])
    return fig


def make_subplots_correlation(source_corr: pd.DataFrame, generated_corr: pd.DataFrame) -> go.Figure:
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Source", "Synthetic"))
    for col, matrix in enumerate((source_corr, generated_corr), start=1):
        fig.add_trace(
            go.Heatmap(z=matrix.values, x=matrix.columns, y=matrix.index, zmin=-1, zmax=1, colorscale="RdBu"),
            row=1,
            col=col,
        )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=45, b=10), showlegend=False)
    return fig


def _show_sidebar() -> None:
    st.sidebar.markdown("## MedSyn")
    st.sidebar.caption("Synthetic cohort research workstation")
    for index, (label, description) in enumerate(STEPS):
        state = "●" if index == st.session_state.current_step else "○"
        if st.sidebar.button(f"{state}  {index + 1:02d}  {label}", key=f"step_{index}", use_container_width=True):
            st.session_state.current_step = index
            st.rerun()
        st.sidebar.caption(description)
    st.sidebar.divider()
    st.sidebar.caption("Evidence is shown separately from target achievement.")


def _page_upload() -> None:
    st.markdown('<div class="section-kicker">01 / source data</div>', unsafe_allow_html=True)
    st.title("Upload a research dataset")
    st.write("Begin with a tabular source cohort. The source remains the reference for every downstream comparison.")
    left, right = st.columns([2, 1])
    with left:
        uploaded = st.file_uploader("CSV or XLSX", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            try:
                st.session_state.uploaded_df = _read_upload(uploaded)
                st.session_state.demo_loaded = False
            except Exception as exc:
                st.error(str(exc))
        if st.button("Load Demo Dataset", type="secondary"):
            st.session_state.uploaded_df = _load_demo()
            st.session_state.demo_loaded = True
            st.success("Demo cohort loaded.")
    data = st.session_state.uploaded_df
    if data is not None:
        summary = _source_summary(data)
        with right:
            st.markdown("### Source summary")
            cols = st.columns(2)
            for col, (label, value) in zip(cols * 3, [("Rows", summary["rows"]), ("Patients", summary["patients"]), ("Columns", summary["columns"]), ("Missing", f'{summary["missing_pct"]}%')]):
                with col:
                    _metric(label, value)
        st.dataframe(data.head(8), use_container_width=True, hide_index=True)
        st.caption(f"Sparsity: {summary['missing']} missing cells ({summary['missing_pct']}% of the source table).")
    _next_button(1, disabled=data is None)


def _page_profile() -> None:
    data = st.session_state.uploaded_df
    if data is None:
        st.warning("Upload a source dataset first.")
        return
    st.markdown('<div class="section-kicker">02 / source profile</div>', unsafe_allow_html=True)
    st.title("Understand the source cohort")
    st.session_state.profile_output = _profile_source(data)
    st.session_state.sparsity_output = _sparsity_source(data)
    c1, c2, c3, c4 = st.columns(4)
    summary = _source_summary(data)
    for col, (label, value) in zip((c1, c2, c3, c4), [("Rows", summary["rows"]), ("Patients", summary["patients"]), ("Numeric fields", len(data.select_dtypes(include=np.number).columns)), ("Missing cells", summary["missing"])]):
        with col:
            _metric(label, value)
    st.markdown("### Dataset DNA")
    dna = st.columns(5)
    for col, label, value in zip(
        dna,
        ("Population", "Temporal coverage", "Variables", "Missingness", "Rare combinations"),
        (
            f'{summary["patients"]:,} patients',
            summary["temporal_coverage"],
            f'{summary["columns"]} ({len(data.select_dtypes(include=np.number).columns)} numeric)',
            f'{summary["missing_pct"]}%',
            _metric_from_mapping(st.session_state.sparsity_output, ("rare_subgroups",), "Computed at feasibility"),
        ),
    ):
        with col:
            _metric(label, value)
    st.markdown("### Schema and missingness")
    schema = pd.DataFrame({"column": data.columns, "dtype": data.dtypes.astype(str), "missing": data.isna().sum().values, "missing %": (data.isna().mean() * 100).round(2).values})
    st.dataframe(schema, use_container_width=True, hide_index=True)
    numeric = data.select_dtypes(include=np.number)
    if not numeric.empty:
        st.markdown("### Compact source statistics")
        st.dataframe(numeric.describe().T.round(2), use_container_width=True)
        st.plotly_chart(px.imshow(numeric.corr(), text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, title="Source numeric correlations"), use_container_width=True)
    _next_button(2)


def _page_cohort() -> None:
    data = st.session_state.uploaded_df
    if data is None:
        st.warning("Upload a source dataset first.")
        return
    st.markdown('<div class="section-kicker">03 / cohort design</div>', unsafe_allow_html=True)
    st.title("Design the target population")
    st.caption("These are population targets, not guarantees. Source evidence is evaluated next.")
    target_n = st.number_input("Target synthetic population size", min_value=1, max_value=1_000_000, value=10_000, step=100)
    diabetic_pct = st.slider("Diabetic target %", 0, 100, 60, disabled="diabetic" not in data.columns)
    age_threshold = st.number_input("Age threshold", min_value=0, max_value=120, value=65)
    age_pct = st.slider("Age-over-threshold target %", 0, 100, 50, disabled="age" not in data.columns)
    adherence_threshold = st.number_input("Medication adherence threshold (%)", min_value=0, max_value=100, value=40)
    adherence_pct = st.slider("Low-adherence target %", 0, 100, 40, disabled="medication_adherence_pct" not in data.columns)
    conditions = []
    if "diabetic" in data.columns:
        conditions.append({"variable": "diabetic", "operator": "==", "value": 1, "target_pct": diabetic_pct})
    if "age" in data.columns:
        conditions.append({"variable": "age", "operator": ">", "value": age_threshold, "target_pct": age_pct})
    if "medication_adherence_pct" in data.columns:
        conditions.append({"variable": "medication_adherence_pct", "operator": "<", "value": adherence_threshold, "target_pct": adherence_pct})
    if len(conditions) < 3:
        st.info("Some demo condition fields are absent; only available variables will be included.")
    st.session_state.cohort_request = {"target_n": int(target_n), "conditions": conditions}
    st.markdown("### Request contract")
    st.dataframe(_condition_frame(st.session_state.cohort_request), use_container_width=True, hide_index=True)
    st.markdown("### Source → target")
    pre_shift = _population_shift(data, st.session_state.cohort_request)
    if pre_shift is not None:
        st.dataframe(pre_shift, use_container_width=True, hide_index=True)
    if st.button("Check Feasibility", type="primary"):
        try:
            st.session_state.feasibility_output = _check_feasibility(data, st.session_state.cohort_request)
        except Exception as exc:
            st.error(f"Feasibility could not be evaluated: {exc}")
            return
        st.session_state.sparse_confirmed = False
        st.session_state.current_step = 3
        st.rerun()


def _page_feasibility() -> None:
    data = st.session_state.uploaded_df
    request = st.session_state.cohort_request
    result = st.session_state.feasibility_output
    if data is None or request is None:
        st.warning("Complete the cohort design first.")
        return
    if result is None:
        result = _check_feasibility(data, request)
        st.session_state.feasibility_output = result
    st.markdown('<div class="section-kicker">04 / feasibility gate</div>', unsafe_allow_html=True)
    st.title("Feasibility gate")
    overall = str(_metric_from_mapping(result, ("overall", "status", "feasibility"), "Unavailable"))
    color = PALETTE["red"] if overall.lower() == "sparse" else PALETTE["amber"] if overall.lower() == "weak" else PALETTE["green"]
    st.markdown(f'<div class="evidence"><strong style="color:{color}">Overall source evidence: {overall}</strong><br>'
                "Target achievement and source evidence are separate questions.</div>", unsafe_allow_html=True)
    st.markdown("### Source evidence by condition")
    conditions = result.get("conditions", []) if isinstance(result, Mapping) else []
    if conditions:
        st.dataframe(_condition_evidence_table(result), use_container_width=True, hide_index=True)
    two_way = result.get("two_way_combinations", []) if isinstance(result, Mapping) else []
    three_way = result.get("three_way_combinations", []) if isinstance(result, Mapping) else []
    if two_way:
        st.markdown("### 2-way source evidence")
        st.dataframe(pd.DataFrame(two_way), use_container_width=True, hide_index=True)
    if three_way:
        st.markdown("### 3-way source evidence")
        st.dataframe(pd.DataFrame(three_way), use_container_width=True, hide_index=True)
    combination = result.get("combination", {}) if isinstance(result, Mapping) else {}
    c1, c2, c3 = st.columns(3)
    with c1:
        _metric("Combination order", combination.get("order", len(request["conditions"])))
    with c2:
        _metric("Source count", combination.get("source_count", "Unavailable"))
    with c3:
        _metric("Source percentage", f'{combination.get("source_pct", "Unavailable")}%')
    requires_confirmation = bool(result.get("requires_confirmation", overall.lower() == "sparse"))
    if requires_confirmation:
        st.warning("Sparse source support. Generation is not recommended without explicit confirmation.")
        st.session_state.sparse_confirmed = st.checkbox(
            "I understand the sparse-source warning and want to generate anyway.",
            key="sparse_confirmation",
        )
    left, right = st.columns(2)
    with left:
        if st.button("Modify Request"):
            st.session_state.current_step = 2
            st.rerun()
    with right:
        if st.button("Continue with confirmation", type="primary", disabled=requires_confirmation and not st.session_state.sparse_confirmed):
            st.session_state.current_step = 4
            st.rerun()


def _page_generation() -> None:
    data, request = st.session_state.uploaded_df, st.session_state.cohort_request
    if data is None or request is None:
        st.warning("Complete upload and cohort design first.")
        return
    st.markdown('<div class="section-kicker">05 / synthesis</div>', unsafe_allow_html=True)
    st.title("Generate the synthetic cohort")
    model_label = st.radio(
        "Generation model",
        ["Gaussian Copula", "CTGAN"],
        index=0 if st.session_state.selected_generation_model == "gaussian_copula" else 1,
        horizontal=True,
    )
    model = "gaussian_copula" if model_label == "Gaussian Copula" else "ctgan"
    st.session_state.selected_generation_model = model
    st.info(f"Requested rows: {request['target_n']:,}  ·  Model: {model_label}")
    if st.button("Run generation", type="primary"):
        st.session_state.generation_complete = False
        with st.spinner(f"Fitting {model_label} and sampling the requested cohort..."):
            try:
                generated = _generate(data, request, model)
                st.session_state.generated_df = generated
                st.session_state.sanity_output = _sanity(data, generated)
                st.session_state.validation_output = _validation(data, generated)
                st.session_state.shift_output = _population_shift(data, request, generated)
                st.session_state.generation_complete = True
                st.success(f"Generated {len(generated):,} rows.")
            except Exception as exc:
                if model == "ctgan":
                    st.warning(f"CTGAN is unavailable or failed in this environment: {exc}")
                    st.info("Gaussian Copula remains available as the reliable default.")
                else:
                    st.error(f"Generation could not be completed: {exc}")
    generated = st.session_state.generated_df
    if generated is not None:
        _metric("Generated row count", f"{len(generated):,}")
        st.markdown("#### Run status")
        for label, complete in (
            ("Learned source population structure", True),
            ("Modeled statistical relationships", True),
            ("Applied cohort request", True),
            ("Generated synthetic records", st.session_state.generation_complete),
            ("Ran mechanical sanity checks", st.session_state.sanity_output is not None),
            ("Ran available validation diagnostics", st.session_state.validation_output is not None),
        ):
            st.write(("✓" if complete else "○") + " " + label)
        _next_button(5)


def _page_sanity() -> None:
    generated = st.session_state.generated_df
    if generated is None:
        st.warning("Generate a cohort first.")
        return
    st.markdown('<div class="section-kicker">06 / mechanical checks</div>', unsafe_allow_html=True)
    st.title("Sanity checks")
    st.caption("These checks assess mechanical output properties, not clinical validity.")
    result = st.session_state.sanity_output
    if isinstance(result, Mapping):
        rows = [
            {"Check": key.replace("_", " ").title(), "Passed": value.get("passed"), "Detail": value.get("detail")}
            for key, value in result.items()
            if isinstance(value, Mapping) and "passed" in value
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.json(result)
    else:
        st.json(result)
    _next_button(6)


def _page_trust() -> None:
    source, generated, request = st.session_state.uploaded_df, st.session_state.generated_df, st.session_state.cohort_request
    if source is None or generated is None:
        st.warning("Generate a cohort first.")
        return
    st.markdown('<div class="section-kicker">07 / research report</div>', unsafe_allow_html=True)
    st.title("Why trust this?")
    st.caption("Trust is evidence across feasibility, quality, privacy, and distribution—not a single score.")
    st.markdown("### 1. Feasibility")
    feasibility = st.session_state.feasibility_output or {}
    st.dataframe(_condition_evidence_table(feasibility), use_container_width=True, hide_index=True)
    st.caption("Source evidence is measured before generation; it is not the same as target achievement.")
    st.markdown("### 2. Quality")
    validation = st.session_state.validation_output
    quality = validation.get("quality", {}) if isinstance(validation, Mapping) else {}
    if isinstance(quality, Mapping):
        score = quality.get("sdmetrics_quality_score")
        if score is not None:
            _metric("SDMetrics quality diagnostic", score)
    st.markdown("**What did the model learn?**")
    st.caption("Observed statistical associations, not causal relationships.")
    relationship_table = _quality_relationship_table(validation or {})
    if relationship_table.empty:
        st.info("Correlation diagnostics are unavailable.")
    else:
        st.dataframe(relationship_table, use_container_width=True, hide_index=True)
    st.markdown("### 3. Privacy")
    privacy = validation.get("privacy", {}) if isinstance(validation, Mapping) else {}
    if isinstance(privacy, Mapping) and privacy.get("value") is not None:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Metric": privacy.get("metric_name"),
                        "Value": privacy.get("value"),
                        "Interpretation": privacy.get("interpretation"),
                    }
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Privacy diagnostic unavailable; no privacy claim is made.")
    st.caption("Diagnostic result; not a guarantee of anonymization, HIPAA compliance, or privacy.")
    st.markdown("### 4. Distribution / correlation")
    quality_cols = [c for c in ("age", "systolic_bp", "activity_steps", "medication_adherence_pct", "pain_score") if c in source and c in generated]
    for selected in quality_cols:
        comparison = pd.concat(
            [source[[selected]].assign(dataset="Source"), generated[[selected]].assign(dataset="Synthetic")],
            ignore_index=True,
        )
        st.plotly_chart(
            px.histogram(
                comparison,
                x=selected,
                color="dataset",
                histnorm="probability density",
                barmode="overlay",
                opacity=.62,
                title=f"{selected}: source vs synthetic",
            ),
            use_container_width=True,
        )
    if quality_cols:
        st.plotly_chart(make_subplots_correlation(source[quality_cols].corr(), generated[quality_cols].corr()), use_container_width=True)
    st.markdown("### Population shift")
    shift_table = (
        st.session_state.shift_output
        if st.session_state.shift_output is not None
        else _population_shift(source, request, generated)
    )
    if shift_table is not None:
        st.dataframe(shift_table, use_container_width=True, hide_index=True)
    st.markdown("### Target achievement")
    st.dataframe(_actual_proportions(generated, request), use_container_width=True, hide_index=True)
    tstr = validation.get("tstr", {}) if isinstance(validation, Mapping) else {}
    if isinstance(tstr, Mapping) and tstr.get("status") == "ok":
        st.markdown("### Task-specific utility")
        st.json(tstr)
        st.caption("TSTR is task-specific utility evidence, not clinical validation.")
    st.markdown("### Edge cohort explorer")
    st.caption("Exploratory stress-test subset; not evidence that the real-world subgroup is clinically represented.")
    edge_conditions = request.get("conditions", [])
    edge_mask = pd.Series(True, index=generated.index)
    for condition in edge_conditions:
        if condition["variable"] not in generated:
            continue
        edge_mask &= {
            "==": generated[condition["variable"]] == condition["value"],
            ">": generated[condition["variable"]] > condition["value"],
            "<": generated[condition["variable"]] < condition["value"],
        }.get(condition["operator"], True)
    st.metric("Synthetic edge records", int(edge_mask.sum()))
    if edge_mask.any():
        st.dataframe(generated.loc[edge_mask].head(25), use_container_width=True, hide_index=True)
    time_col = next(
        (c for c in source.columns if c.lower() in {"month", "date", "time", "timestamp"}), None
    )
    generation = _import_optional("backend.generation")
    longitudinal_fn = getattr(generation, "generate_longitudinal", None) if generation else None
    if time_col and longitudinal_fn:
        st.markdown("### Longitudinal explorer")
        st.caption("Trajectory bootstrap resamples observed longitudinal change patterns; it does not mechanistically model disease progression.")
        if st.button("Build trajectory comparison"):
            try:
                baseline = generated.sort_values(time_col).groupby(
                    next((c for c in generated.columns if "patient" in c.lower() and "id" in c.lower()), generated.columns[0]),
                    as_index=False,
                ).first()
                st.session_state.longitudinal_df = longitudinal_fn(source, baseline, time_col)
            except Exception as exc:
                st.warning(f"Longitudinal explorer unavailable: {exc}")
        longitudinal = st.session_state.longitudinal_df
        if longitudinal is not None:
            trajectory_col = st.selectbox(
                "Trajectory variable",
                [c for c in ("systolic_bp", "medication_adherence_pct", "pain_score", "activity_steps") if c in source and c in longitudinal],
                key="trajectory_variable",
            )
            real_line = source.groupby(time_col)[trajectory_col].mean().reset_index().assign(dataset="Real")
            synthetic_line = longitudinal.groupby(time_col)[trajectory_col].mean().reset_index().assign(dataset="Synthetic")
            st.plotly_chart(px.line(pd.concat([real_line, synthetic_line]), x=time_col, y=trajectory_col, color="dataset", markers=True, title="Real vs synthetic trajectory"), use_container_width=True)
    _next_button(7)


def _page_export() -> None:
    generated = st.session_state.generated_df
    if generated is None:
        st.warning("Generate a cohort first.")
        return
    st.markdown('<div class="section-kicker">08 / export</div>', unsafe_allow_html=True)
    st.title("Export the research cohort")
    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in ((c1, "Generated patients", len(generated)), (c2, "Model", st.session_state.selected_generation_model), (c3, "Validation", "Completed" if st.session_state.validation_output else "Unavailable"), (c4, "Feasibility", _metric_from_mapping(st.session_state.feasibility_output, ("overall", "status"), "Unavailable"))):
        with col:
            _metric(label, value)
    csv = generated.to_csv(index=False).encode("utf-8")
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        generated.to_excel(writer, index=False, sheet_name="synthetic_cohort")
    st.download_button("Download CSV", csv, "medsyn_synthetic_cohort.csv", "text/csv", type="primary")
    st.download_button("Download Excel", excel_buffer.getvalue(), "medsyn_synthetic_cohort.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    report = json.dumps(
        {
            "cohort_request": st.session_state.cohort_request,
            "feasibility": st.session_state.feasibility_output,
            "sanity": st.session_state.sanity_output,
            "validation": st.session_state.validation_output,
        },
        default=str,
        indent=2,
    ).encode("utf-8")
    st.download_button("Download Validation Report", report, "medsyn_validation_report.json", "application/json")


def _next_button(next_step: int, disabled: bool = False) -> None:
    if st.button("Continue", key=f"continue_{next_step}", type="primary", disabled=disabled):
        st.session_state.current_step = next_step
        st.rerun()


def main() -> None:
    _init_state()
    _style()
    _show_sidebar()
    _banner()
    pages = (_page_upload, _page_profile, _page_cohort, _page_feasibility, _page_generation, _page_sanity, _page_trust, _page_export)
    pages[st.session_state.current_step]()


if __name__ == "__main__":
    main()
