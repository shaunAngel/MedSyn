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
        "privacy_attack_output": None,
        "model_comparison_output": None,
        "shift_output": None,
        "longitudinal_df": None,
        "current_step": 0,
        "selected_generation_model": "gaussian_copula",
        "sparse_confirmed": False,
        "sparse_confirmation": False,
        "demo_loaded": False,
        "generation_complete": False,
        "generation_model_used": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _style() -> None:
    st.markdown(
        f"""
        <style>
        :root {{ color-scheme: light; }}
        .stApp, [data-testid="stAppViewContainer"] {{ background: #fbfcfd; color: {PALETTE["navy"]}; }}
        [data-testid="stSidebar"] {{ background: {PALETTE["pale"]}; border-right: 1px solid {PALETTE["line"]}; }}
        [data-testid="stSidebar"] *, .stApp p, .stApp label, .stApp small, .stApp [data-testid="stCaptionContainer"] {{
            color: {PALETTE["slate"]};
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label,
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            color: {PALETTE["navy"]} !important;
        }}
        [data-testid="stWidgetLabel"] p {{ font-weight: 600; }}
        .stApp input, .stApp textarea, .stApp [data-baseweb="select"] * {{
            color: {PALETTE["navy"]} !important;
            background: #ffffff !important;
        }}
        .stApp input::placeholder {{ color: #71808A !important; }}
        [data-testid="stSidebar"] button, [data-testid="stSidebar"] button * {{
            color: {PALETTE["navy"]} !important;
        }}
        .research-banner {{ border: 1px solid #E4C98A; background: #FFF8E8; color: #684D1E;
            padding: .5rem .8rem; margin-bottom: .85rem; font-size: .84rem; }}
        .metric-card {{ background: white; border: 1px solid {PALETTE["line"]}; border-radius: 3px; padding: .55rem .7rem; min-height: 64px; }}
        .metric-label {{ color: {PALETTE["slate"]}; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; }}
        .metric-value {{ color: {PALETTE["navy"]}; font: 600 1.05rem ui-monospace, SFMono-Regular, Menlo, monospace; margin-top: .2rem; }}
        .section-kicker {{ color: {PALETTE["navy"]}; font: 600 .7rem ui-monospace, SFMono-Regular, Menlo, monospace;
            letter-spacing: .1em; text-transform: uppercase; margin-bottom: .15rem; }}
        .evidence {{ border-left: 3px solid {PALETTE["blue"]}; background: white; padding: .7rem .85rem; border-top: 1px solid {PALETTE["line"]};
            border-right: 1px solid {PALETTE["line"]}; border-bottom: 1px solid {PALETTE["line"]}; }}
        .target-preview, .combo-evidence {{ background: #ffffff; border: 1px solid {PALETTE["line"]}; padding: .75rem .9rem; margin: .55rem 0 .85rem; }}
        .target-preview strong, .combo-evidence strong {{ font: 600 .72rem ui-monospace, SFMono-Regular, Menlo, monospace;
            letter-spacing: .1em; color: {PALETTE["navy"]}; }}
        .target-preview p, .combo-evidence p {{ margin: .28rem 0 0; color: {PALETTE["navy"]}; font-size: .92rem; }}
        .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
        .structure-row {{ display: flex; gap: 1.2rem; border-bottom: 1px solid {PALETTE["line"]}; padding: .4rem 0; }}
        .structure-label {{ width: 11rem; color: {PALETTE["slate"]}; font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; }}
        .structure-value {{ color: {PALETTE["navy"]}; font-size: .9rem; }}
        .check-line {{ font: 500 .9rem ui-monospace, SFMono-Regular, Menlo, monospace; color: {PALETTE["navy"]}; margin: .2rem 0; }}
        .stButton > button, [data-testid="stDownloadButton"] button {{
            border-radius: 3px !important; min-height: 2.2rem !important; font-weight: 600 !important;
        }}
        [data-testid="stBaseButton-primary"], [data-testid="stDownloadButton"] button[kind="primary"] {{
            background: {PALETTE["blue"]} !important; border: 1px solid {PALETTE["blue"]} !important; color: #ffffff !important;
        }}
        [data-testid="stBaseButton-primary"] *, [data-testid="stDownloadButton"] button[kind="primary"] * {{ color: #ffffff !important; }}
        [data-testid="stBaseButton-secondary"], [data-testid="stDownloadButton"] button[kind="secondary"] {{
            background: #ffffff !important; border: 1px solid {PALETTE["navy"]} !important; color: {PALETTE["navy"]} !important;
        }}
        [data-testid="stBaseButton-secondary"] *, [data-testid="stDownloadButton"] button[kind="secondary"] * {{ color: {PALETTE["navy"]} !important; }}
        [data-testid="stBaseButton-secondary"]:hover, [data-testid="stDownloadButton"] button[kind="secondary"]:hover {{
            background: {PALETTE["pale"]} !important; color: {PALETTE["navy"]} !important;
        }}
        .stButton > button:disabled {{ color: #7A8790 !important; background: #E8EDF0 !important; border-color: #CBD5DA !important; }}
        h1 {{ font-size: 1.55rem !important; letter-spacing: -.02em; margin-bottom: .15rem !important; }}
        h2, h3 {{ letter-spacing: -.01em; font-size: 1.12rem !important; }}
        [data-testid="stVerticalBlock"] > div {{ gap: .45rem; }}
        [data-testid="stMainBlockContainer"] {{ padding-top: 1.2rem; }}
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
    ingest = _import_optional("data_ingest")
    detect = getattr(ingest, "detect_schema", None) if ingest else None
    if detect:
        schema = detect(data)
        return {"schema": schema, "dtypes": data.dtypes.astype(str).to_dict()}
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
    module = _import_optional("sparsity")
    function = getattr(module, "compute_sparsity", None) if module else None
    if function:
        dimensions = [d for d in ("diabetic", "age_over_65", "low_adherence") if d in data or d in {"age_over_65", "low_adherence"}]
        try:
            return function(data, dimensions)
        except (TypeError, ValueError):
            pass
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
    common = [column for column in source.columns if column in generated.columns]
    source_v = source.loc[:, common] if common else source
    generated_v = generated.loc[:, common] if common else generated
    result: Dict[str, Any] = {}
    for function_name, result_key, args in (
            ("compute_quality_metrics", "quality", (source_v, generated_v)),
            ("compute_privacy_metrics", "privacy", (source_v, generated_v)),
            ("compute_missingness_similarity", "missingness", (source_v, generated_v)),
    ):
        function = getattr(module, function_name, None)
        if function is None:
            result[result_key] = {"status": "Unavailable"}
            continue
        try:
            result[result_key] = function(*args)
        except Exception as exc:
            result[result_key] = {"status": "Unavailable", "error": str(exc)}
    tstr = getattr(module, "compute_tstr", None)
    if tstr:
        target = next(
            (column for column in ("diabetic", "pain_score", "systolic_bp") if column in source_v and column in generated_v),
            None,
        )
        if target:
            try:
                result["tstr"] = tstr(source, generated, target)
            except Exception as exc:
                result["tstr"] = {"status": "Unavailable", "error": str(exc)}
        else:
            result["tstr"] = {"status": "Unavailable"}
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


def _compact_shift_table(shift_table: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if shift_table is None or shift_table.empty:
        return shift_table
    columns = [
        column
        for column in (
            "Variable",
            "Source %",
            "Target %",
            "Generated %",
            "Target Shift (Δ)",
            "Target Error (Δ)",
            "Target Status",
        )
        if column in shift_table.columns
    ]
    return shift_table.loc[:, columns] if columns else shift_table


def _trajectory_summary(
        data: pd.DataFrame,
        time_col: str,
        value_col: str,
        label: str,
) -> pd.DataFrame:
    """Compute comparable, month-ordered group means for trajectory display."""
    frame = data[[time_col, value_col]].copy()
    frame[value_col] = pd.to_numeric(frame[value_col], errors="coerce")
    frame = frame.dropna(subset=[time_col, value_col])
    if frame.empty:
        return pd.DataFrame(columns=[time_col, value_col, "dataset"])
    numeric_time = pd.to_numeric(frame[time_col], errors="coerce")
    if numeric_time.notna().all():
        frame["_time_order"] = numeric_time
        frame = frame.sort_values("_time_order")
    else:
        frame = frame.sort_values(time_col)
    summary = frame.groupby(time_col, sort=False, as_index=False)[value_col].mean()
    summary["dataset"] = label
    return summary


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
                "Source correlation": values.get("source_correlation"),
                "Synthetic correlation": values.get("synthetic_correlation"),
                "Difference": values.get("difference"),
            }
        )
    return pd.DataFrame(rows)


def _privacy_attack(source: pd.DataFrame, model: str) -> Dict[str, Any]:
    """Run the isolated privacy module only when explicitly requested in the UI."""
    module = _import_optional("privacy")
    function = getattr(module, "run_membership_inference_simulation", None) if module else None
    if function is None:
        return {"status": "error", "error": "Privacy simulation module is unavailable."}
    return function(source, generator_model=model)


def _model_comparison(source: pd.DataFrame, request: Mapping[str, Any]) -> Any:
    """Run an explicit synthesis-model evidence comparison."""
    module = _import_optional("backend.model_comparison")
    function = getattr(module, "compare_generation_models", None) if module else None

    if function is None:
        return {
            "status": "Unavailable",
            "error": "Model comparison backend is unavailable.",
        }

    try:
        target_n = min(int(request.get("target_n", 1000)), 1000)
        return function(
            source,
            request,
            models=("gaussian_copula", "ctgan"),
            target_n=target_n,
            random_state=42,
            run_privacy=True,
        )
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


def _privacy_distance_chart(result: Mapping[str, Any]) -> go.Figure:
    distances = pd.DataFrame(
        {
            "Nearest-neighbor distance": list(result.get("train_distances", []))
                                         + list(result.get("holdout_distances", [])),
            "Group": (["Training members"] * len(result.get("train_distances", [])))
                     + (["Held-out non-members"] * len(result.get("holdout_distances", []))),
        }
    )
    fig = px.histogram(
        distances,
        x="Nearest-neighbor distance",
        color="Group",
        histnorm="probability density",
        barmode="overlay",
        opacity=.6,
        color_discrete_map={"Training members": PALETTE["blue"], "Held-out non-members": PALETTE["amber"]},
        title="Nearest-neighbor distance distribution",
        template="plotly_white",
    )
    fig.add_vline(x=float(result["threshold_example"]), line_dash="dash", line_color=PALETTE["slate"], annotation_text="illustrative threshold")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=45, b=10))
    return fig


def _privacy_roc_chart(result: Mapping[str, Any]) -> go.Figure:
    curve = result.get("roc_curve", {})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve.get("fpr", []), y=curve.get("tpr", []), mode="lines", name=f"Attack AUROC {result['attack_auroc']:.2f}", line=dict(color=PALETTE["blue"], width=3)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random", line=dict(color=PALETTE["slate"], dash="dash")))
    fig.update_layout(title="Membership-inference ROC curve", xaxis_title="False positive rate", yaxis_title="True positive rate", height=300, margin=dict(l=10, r=10, t=45, b=10), template="plotly_white", legend=dict(orientation="h", y=1.14, x=0))
    return fig


def _metric_from_mapping(data: Any, keys: Iterable[str], default: str = "Unavailable") -> Any:
    if isinstance(data, Mapping):
        for key in keys:
            if key in data and not isinstance(data[key], (dict, list, tuple)):
                return data[key]
    return default


def _unavailable(value: Any, empty: str = "Unavailable") -> str:
    if value is None or value == "" or (isinstance(value, float) and not np.isfinite(value)):
        return empty
    if isinstance(value, str) and value.strip().lower() in {"none", "nan"}:
        return empty
    return str(value)


def _model_label(model: Optional[str]) -> str:
    if model == "gaussian_copula":
        return "Gaussian Copula"
    if model == "ctgan":
        return "CTGAN"
    return _unavailable(model)


def _patient_time_cols(data: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
    ingest = _import_optional("data_ingest")
    detect = getattr(ingest, "detect_schema", None) if ingest else None
    if detect:
        schema = detect(data)
        return schema.get("patient_id_col"), schema.get("time_col")
    summary = _source_summary(data)
    return (
        next((c for c in data.columns if "patient" in c.lower() and "id" in c.lower()), None),
        summary.get("time_col"),
    )


def _fresh_identifiers_assigned(source: pd.DataFrame, generated: pd.DataFrame) -> bool:
    patient_col, _ = _patient_time_cols(generated)
    if not patient_col or patient_col not in generated.columns or patient_col not in source.columns:
        return False
    overlap = set(generated[patient_col].dropna()) & set(source[patient_col].dropna())
    return len(overlap) == 0


def _condition_display_table(result: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for condition in result.get("conditions", []):
        rows.append(
            {
                "Condition": condition.get("Condition") or condition.get("variable"),
                "Source patients": condition.get("Source count", condition.get("source_count")),
                "Source %": condition.get("Source %", condition.get("source_pct")),
                "Evidence availability": condition.get("Evidence", condition.get("evidence", condition.get("status"))),
                "Target %": condition.get("Target %", condition.get("target_pct")),
            }
        )
    return pd.DataFrame(rows)


def _sanity_display_rows(result: Any) -> pd.DataFrame:
    if not isinstance(result, Mapping):
        return pd.DataFrame()
    rows = []
    checks = result.get("checks")
    if isinstance(checks, list):
        for item in checks:
            if not isinstance(item, Mapping):
                continue
            status = str(item.get("status", "WARN")).upper()
            if status not in {"PASS", "WARN", "FAIL"}:
                status = "WARN"
            rows.append({"Check": item.get("check"), "Status": status, "Detail": item.get("detail")})
        return pd.DataFrame(rows)
    for key, value in result.items():
        if not isinstance(value, Mapping) or "passed" not in value:
            continue
        rows.append(
            {
                "Check": key.replace("_", " ").title(),
                "Status": "PASS" if value.get("passed") else "FAIL",
                "Detail": value.get("detail"),
            }
        )
    return pd.DataFrame(rows)


def _comparison_display_table(result: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for item in result.get("results", []):
        if not isinstance(item, Mapping):
            continue
        privacy_value = item.get("privacy_attack_auroc")
        privacy_note = str(item.get("privacy_note") or "")
        if privacy_value is not None:
            privacy_status = f"{privacy_value:.3f}"
        elif "not run" in privacy_note.lower():
            privacy_status = "Not run"
        elif item.get("status") == "error":
            privacy_status = "Unavailable"
        else:
            privacy_status = "Not run" if not privacy_note else privacy_note
        rows.append(
            {
                "Model": _model_label(item.get("model")),
                "Generation time": _unavailable(
                    None if item.get("generation_seconds") is None else f"{item['generation_seconds']:.2f}s"
                ),
                "Records": _unavailable(item.get("n_records")),
                "Quality diagnostic": _unavailable(item.get("quality_score")),
                "Correlation difference": _unavailable(item.get("mean_correlation_difference")),
                "Missingness difference": _unavailable(item.get("mean_missingness_difference")),
                "Target deviation": _unavailable(item.get("target_deviation")),
                "Privacy status": privacy_status,
            }
        )
    return pd.DataFrame(rows)


def _tstr_display_table(tstr: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for label, key in (("Synthetic → Real", "synthetic_to_real"), ("Real → Real", "real_to_real")):
        metrics = tstr.get(key, {})
        if not isinstance(metrics, Mapping):
            metrics = {}
        rows.append(
            {
                "Training": label,
                "Accuracy": _unavailable(metrics.get("accuracy")),
                "AUROC": _unavailable(metrics.get("roc_auc")),
            }
        )
    return pd.DataFrame(rows)


def _structure_row(label: str, value: Any) -> None:
    st.markdown(
        f'<div class="structure-row"><div class="structure-label">{label}</div>'
        f'<div class="structure-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def _check_line(complete: bool, label: str) -> None:
    mark = "✓" if complete else "○"
    st.markdown(f'<div class="check-line">{mark} {label}</div>', unsafe_allow_html=True)


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
        state = "●" if index == st.session_state.current_step else "✓" if index < st.session_state.current_step else "○"
        if st.sidebar.button(f"{state}  {index + 1:02d}  {label}", key=f"step_{index}", use_container_width=True):
            st.session_state.current_step = index
            st.rerun()
        st.sidebar.caption(description)
    st.sidebar.divider()
    st.sidebar.caption("Upload → profile → design → feasibility → generate → integrity → evidence → export.")
    st.sidebar.caption("Source evidence is shown separately from target achievement.")


def _page_upload() -> None:
    st.markdown('<div class="section-kicker">01 / source cohort</div>', unsafe_allow_html=True)
    st.title("Source cohort")
    st.caption("Upload a longitudinal patient dataset to begin cohort analysis.")
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
        metrics = (
            ("Rows", f"{summary['rows']:,}"),
            ("Patients", f"{summary['patients']:,}"),
            ("Variables", summary["columns"]),
            ("Missing cells", f"{summary['missing']:,}"),
            ("Temporal coverage", summary["temporal_coverage"]),
        )
        cols = st.columns(len(metrics))
        for col, (label, value) in zip(cols, metrics):
            with col:
                _metric(label, value)
        profile = _profile_source(data)
        structure = profile.get("schema", {}) if isinstance(profile, Mapping) else {}
        st.markdown("### Detected structure")
        numeric = structure.get("numeric_cols") or list(data.select_dtypes(include=np.number).columns)
        categorical = structure.get("categorical_cols") or [c for c in data.columns if c not in numeric]
        _structure_row("Patient identifier", structure.get("patient_id_col") or "Not detected")
        _structure_row("Time variable", structure.get("time_col") or summary["time_col"] or "Not detected")
        _structure_row("Numeric variables", ", ".join(map(str, numeric)) or "None detected")
        _structure_row("Categorical variables", ", ".join(map(str, categorical)) or "None detected")
    _next_button(1, disabled=data is None)


def _page_profile() -> None:
    data = st.session_state.uploaded_df
    if data is None:
        st.warning("Upload a source dataset first.")
        return
    st.markdown('<div class="section-kicker">02 / source profile</div>', unsafe_allow_html=True)
    st.title("Profile")
    st.session_state.profile_output = _profile_source(data)
    st.session_state.sparsity_output = _sparsity_source(data)
    summary = _source_summary(data)
    c1, c2, c3, c4 = st.columns(4)
    for col, (label, value) in zip(
            (c1, c2, c3, c4),
            (
                    ("Patients", f"{summary['patients']:,}"),
                    ("Observations", f"{summary['rows']:,}"),
                    ("Variables", summary["columns"]),
                    ("Missingness", f'{summary["missing_pct"]}%'),
            ),
    ):
        with col:
            _metric(label, value)
    left, right = st.columns([1.15, 1])
    schema = pd.DataFrame(
        {
            "Variable": data.columns,
            "Type": data.dtypes.astype(str).values,
            "Missingness": (data.isna().mean() * 100).round(2).values,
            "Unique values": [data[column].nunique(dropna=True) for column in data],
        }
    )
    with left:
        st.markdown("### Variable profile")
        st.dataframe(schema, use_container_width=True, hide_index=True)
    with right:
        st.markdown("### Source distributions")
        candidates = [
            column
            for column in (
                "age",
                "systolic_bp",
                "activity_steps",
                "medication_adherence_pct",
                "pain_score",
            )
            if column in data.columns
        ]
        for column in candidates[:3]:
            fig = px.histogram(
                data,
                x=column,
                nbins=30,
                title=column.replace("_", " "),
                template="plotly_white",
                color_discrete_sequence=[PALETTE["blue"]],
            )
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10), bargap=0.05)
            st.plotly_chart(fig, use_container_width=True)
        if not candidates:
            st.caption("No preferred source distribution variables were detected.")
    st.markdown("### Longitudinal coverage")
    time_col = summary.get("time_col")
    if time_col and time_col in data.columns:
        patient_col, _ = _patient_time_cols(data)
        coverage = data.groupby(time_col).size().reset_index(name="observations")
        if patient_col and patient_col in data.columns:
            coverage["patients"] = data.groupby(time_col)[patient_col].nunique().values
        fig = px.bar(
            coverage,
            x=time_col,
            y="observations",
            title=f"Observations by {time_col}",
            template="plotly_white",
            color_discrete_sequence=[PALETTE["navy"]],
        )
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
        observations_per_patient = round(summary["rows"] / max(summary["patients"], 1), 2)
        st.caption(
            f"Time variable: {time_col} · Range: {summary['temporal_coverage']} · "
            f"Observations per patient: {observations_per_patient}"
        )
    else:
        st.caption("No time variable was detected in the source dataset.")
    _next_button(2)


def _page_cohort() -> None:
    data = st.session_state.uploaded_df
    if data is None:
        st.warning("Upload a source dataset first.")
        return
    st.markdown('<div class="section-kicker">03 / cohort design</div>', unsafe_allow_html=True)
    st.title("Design the target cohort")
    st.caption(
        "Specify the population you want to generate. MedSyn checks whether "
        "the source data supports the requested combination."
    )
    target_n = st.number_input(
        "Target population",
        min_value=1,
        max_value=1_000_000,
        value=10_000,
        step=100,
    )
    diabetic_pct = 0
    age_threshold = 65
    age_pct = 0
    adherence_threshold = 40
    adherence_pct = 0
    left, right = st.columns(2, gap="medium")
    with left:
        diabetic_pct = st.slider(
            "Diabetic proportion",
            0,
            100,
            60,
            disabled="diabetic" not in data.columns,
            key="diabetic_target",
        )
        age_threshold = st.number_input(
            "Age threshold",
            min_value=0,
            max_value=120,
            value=65,
            key="age_threshold",
        )
        age_pct = st.slider(
            "Age-over-threshold proportion",
            0,
            100,
            50,
            disabled="age" not in data.columns,
            key="age_target",
        )
    with right:
        adherence_threshold = st.number_input(
            "Adherence threshold",
            min_value=0,
            max_value=100,
            value=40,
            key="adherence_threshold",
        )
        adherence_pct = st.slider(
            "Low-adherence proportion",
            0,
            100,
            40,
            disabled="medication_adherence_pct" not in data.columns,
            key="adherence_target",
        )
    conditions = []
    preview_lines = [f"{int(target_n):,} synthetic records"]
    if "diabetic" in data.columns:
        conditions.append({"variable": "diabetic", "operator": "==", "value": 1, "target_pct": diabetic_pct})
        preview_lines.append(f"{diabetic_pct}% diabetic")
    if "age" in data.columns:
        conditions.append({"variable": "age", "operator": ">", "value": age_threshold, "target_pct": age_pct})
        preview_lines.append(f"{age_pct}% age > {age_threshold}")
    if "medication_adherence_pct" in data.columns:
        conditions.append(
            {
                "variable": "medication_adherence_pct",
                "operator": "<",
                "value": adherence_threshold,
                "target_pct": adherence_pct,
            }
        )
        preview_lines.append(f"{adherence_pct}% low adherence")
    if len(conditions) < 3:
        st.info("Some requested condition fields are absent; only available variables will be included.")
    st.session_state.cohort_request = {"target_n": int(target_n), "conditions": conditions}
    st.markdown(
        '<div class="target-preview"><strong>TARGET COHORT</strong>'
        + "".join(f"<p>{line}</p>" for line in preview_lines)
        + "</div>",
        unsafe_allow_html=True,
        )
    if st.button("Check source feasibility", type="primary", use_container_width=True):
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
    st.markdown('<div class="section-kicker">04 / feasibility</div>', unsafe_allow_html=True)
    st.title("Can the source support this cohort?")
    st.caption(
        "Feasibility measures how much direct evidence exists in the source "
        "population for the requested subgroup."
    )
    if result is None:
        st.info("Run Check source feasibility from the cohort design step before reviewing evidence.")
        if st.button("Check source feasibility", type="primary"):
            try:
                st.session_state.feasibility_output = _check_feasibility(data, request)
            except Exception as exc:
                st.error(f"Feasibility could not be evaluated: {exc}")
                return
            st.session_state.sparse_confirmed = False
            st.rerun()
        return
    overall = str(_metric_from_mapping(result, ("overall", "status", "feasibility"), "Unavailable"))
    color = (
        PALETTE["red"]
        if overall.lower() == "sparse"
        else PALETTE["amber"]
        if overall.lower() == "weak"
        else PALETTE["green"]
    )
    st.markdown(
        f'<div class="evidence"><strong style="color:{color}">Overall source evidence: {overall}</strong><br>'
        "Source evidence and target achievement are separate questions.</div>",
        unsafe_allow_html=True,
    )
    conditions = result.get("conditions", []) if isinstance(result, Mapping) else []
    if conditions:
        st.markdown("### Source evidence by condition")
        st.dataframe(_condition_display_table(result), use_container_width=True, hide_index=True)
    combination = result.get("combination", {}) if isinstance(result, Mapping) else {}
    combo_label = combination.get("label")
    if not combo_label:
        names = [item.get("variable") for item in request.get("conditions", [])]
        combo_label = " & ".join(str(name) for name in names if name)
    evidence = combination.get("Evidence", combination.get("evidence", overall))
    st.markdown(
        '<div class="combo-evidence"><strong>COMBINATION EVIDENCE</strong>'
        f'<p class="mono">{combo_label}</p>'
        f'<p>Source patients: {_unavailable(combination.get("source_count"))}</p>'
        f'<p>Source percentage: {_unavailable(combination.get("source_pct"))}%</p>'
        f"<p>Evidence: {_unavailable(evidence)}</p></div>",
        unsafe_allow_html=True,
    )
    if str(evidence).lower() == "sparse" or overall.lower() == "sparse":
        st.warning(
            "This combination is sparsely represented in the source data. "
            "Generated records may therefore involve extrapolation beyond "
            "well-supported source evidence."
        )
    requires_confirmation = bool(result.get("requires_confirmation", overall.lower() == "sparse"))
    if requires_confirmation:
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
        if st.button(
                "Continue with confirmation",
                type="primary",
                disabled=requires_confirmation and not st.session_state.sparse_confirmed,
        ):
            st.session_state.current_step = 4
            st.rerun()


def _page_generation() -> None:
    data, request = st.session_state.uploaded_df, st.session_state.cohort_request
    if data is None or request is None:
        st.warning("Complete upload and cohort design first.")
        return
    st.markdown('<div class="section-kicker">05 / generation</div>', unsafe_allow_html=True)
    st.title("Generate synthetic cohort")
    model_label = st.radio(
        "Generation model",
        ["Gaussian Copula", "CTGAN"],
        index=0 if st.session_state.selected_generation_model == "gaussian_copula" else 1,
        horizontal=True,
        help="Gaussian Copula is the default synthesizer. CTGAN is an alternative method, not a ranked replacement.",
    )
    model = "gaussian_copula" if model_label == "Gaussian Copula" else "ctgan"
    st.session_state.selected_generation_model = model
    if model == "gaussian_copula":
        st.caption("Gaussian Copula is the default generation method for this workstation.")
    patient_col, _ = _patient_time_cols(data)
    source_patients = data[patient_col].nunique() if patient_col and patient_col in data.columns else len(data)
    info = st.columns(3)
    with info[0]:
        _metric("Target records", f"{request['target_n']:,}")
    with info[1]:
        _metric("Selected model", "Gaussian Copula (default)" if model == "gaussian_copula" else "CTGAN")
    with info[2]:
        _metric("Source patients used for training", f"{source_patients:,}")
    if st.button("Run generation", type="primary"):
        st.session_state.generation_complete = False
        st.session_state.privacy_attack_output = None
        st.session_state.longitudinal_df = None
        with st.spinner(f"Fitting {model_label} and sampling the requested cohort..."):
            try:
                generated = _generate(data, request, model)
                st.session_state.generated_df = generated
                st.session_state.sanity_output = _sanity(data, generated)
                st.session_state.validation_output = _validation(data, generated)
                st.session_state.shift_output = _population_shift(data, request, generated)
                st.session_state.generation_model_used = model
                st.session_state.generation_complete = True
                st.success(f"Generated {len(generated):,} rows.")
            except Exception as exc:
                if model == "ctgan":
                    st.warning(f"CTGAN is unavailable or failed in this environment: {exc}")
                    st.info("Gaussian Copula remains available as the default method.")
                else:
                    st.error(f"Generation could not be completed: {exc}")
    generated = st.session_state.generated_df
    if generated is not None and st.session_state.generation_complete:
        used_model = st.session_state.generation_model_used or model
        out = st.columns(2)
        with out[0]:
            _metric("Generated records", f"{len(generated):,}")
        with out[1]:
            _metric("Generation model", _model_label(used_model))
        st.markdown("#### Completed operations")
        _check_line(True, "Synthetic records generated")
        _check_line(_fresh_identifiers_assigned(data, generated), "Fresh identifiers assigned")
        _check_line(st.session_state.sanity_output is not None, "Mechanical checks completed")
        _check_line(st.session_state.validation_output is not None, "Validation diagnostics available")
        _next_button(5)


def _page_sanity() -> None:
    generated = st.session_state.generated_df
    if generated is None:
        st.warning("Generate a cohort first.")
        return
    st.markdown('<div class="section-kicker">06 / mechanical checks</div>', unsafe_allow_html=True)
    st.title("Mechanical sanity checks")
    st.caption("These checks assess output integrity, not clinical validity.")
    rows = _sanity_display_rows(st.session_state.sanity_output)
    if rows.empty:
        st.info("Mechanical sanity results are unavailable.")
    else:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    _next_button(6)


def _page_trust() -> None:
    source, generated, request = (
        st.session_state.uploaded_df,
        st.session_state.generated_df,
        st.session_state.cohort_request,
    )
    if source is None or generated is None:
        st.warning("Generate a cohort first.")
        return
    st.markdown('<div class="section-kicker">07 / research evidence</div>', unsafe_allow_html=True)
    st.title("Why trust this?")
    st.caption(
        "Trust is evidence across feasibility, fidelity, privacy, utility, "
        "and population shift — not a single score."
    )
    validation = st.session_state.validation_output
    feasibility = st.session_state.feasibility_output or {}

    st.markdown("### 1. Source evidence")
    st.caption("Source evidence is measured before generation.")
    ev_col, ach_col = st.columns(2)
    with ev_col:
        st.markdown("**SOURCE EVIDENCE**")
        if isinstance(feasibility, Mapping) and feasibility.get("conditions"):
            st.dataframe(_condition_display_table(feasibility), use_container_width=True, hide_index=True)
        else:
            st.caption("Feasibility has not been evaluated.")
    with ach_col:
        st.markdown("**TARGET ACHIEVEMENT**")
        achievement = _actual_proportions(generated, request) if request else pd.DataFrame()
        if not achievement.empty:
            st.dataframe(achievement, use_container_width=True, hide_index=True)
        else:
            st.caption("Generated proportions are unavailable.")

    st.markdown("### 2. Fidelity")
    quality = validation.get("quality", {}) if isinstance(validation, Mapping) else {}
    if isinstance(quality, Mapping) and quality.get("sdmetrics_quality_score") is not None:
        _metric("SDMetrics quality diagnostic", quality.get("sdmetrics_quality_score"))
    else:
        _metric("SDMetrics quality diagnostic", "Unavailable")
    quality_cols = [
        column
        for column in (
            "age",
            "systolic_bp",
            "activity_steps",
            "medication_adherence_pct",
            "pain_score",
        )
        if column in source.columns and column in generated.columns
    ]
    if quality_cols:
        selected = st.selectbox("Variable", quality_cols, key="trust_distribution")
        comparison = pd.concat(
            [
                source[[selected]].assign(dataset="Source"),
                generated[[selected]].assign(dataset="Synthetic"),
            ],
            ignore_index=True,
        )
        fig = px.histogram(
            comparison,
            x=selected,
            color="dataset",
            histnorm="probability density",
            barmode="overlay",
            opacity=0.62,
            title=f"{selected.replace('_', ' ')}: Source vs Synthetic",
            template="plotly_white",
            color_discrete_map={"Source": PALETTE["navy"], "Synthetic": PALETTE["blue"]},
        )
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=45, b=10), legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 3. Statistical relationships")
    st.caption("Observed statistical associations — not causal relationships.")
    relationship_table = _quality_relationship_table(validation or {})
    if relationship_table.empty:
        st.info("Correlation diagnostics are unavailable.")
    else:
        st.dataframe(relationship_table, use_container_width=True, hide_index=True)

    st.markdown("### 4. Privacy — we tried to break it")
    st.markdown("**Can an attack distinguish patients used during training from patients held out from training?**")
    st.caption(
        "This is a simulated membership-inference attack under a specific threat model. "
        "It is not a formal privacy guarantee."
    )
    attack_result = st.session_state.privacy_attack_output
    button_label = "Re-run privacy attack" if attack_result is not None else "Run privacy attack"
    if st.button(button_label, type="primary", key="run_privacy_attack"):
        with st.spinner("Training the attack-only generator on patient-disjoint source data..."):
            st.session_state.privacy_attack_output = _privacy_attack(
                source,
                st.session_state.generation_model_used or st.session_state.selected_generation_model,
                )
        attack_result = st.session_state.privacy_attack_output
    if isinstance(attack_result, Mapping):
        if attack_result.get("status") != "ok":
            st.warning(f"Privacy attack unavailable: {attack_result.get('error', 'Unknown error')}")
        else:
            attack_metrics = st.columns(3)
            for col, label, value in zip(
                    attack_metrics,
                    ("Attack AUROC", "Training patients", "Held-out patients"),
                    (
                            f"{attack_result['attack_auroc']:.2f}",
                            attack_result["n_train_patients"],
                            attack_result["n_holdout_patients"],
                    ),
            ):
                with col:
                    _metric(label, value)
            distance_metrics = pd.DataFrame(
                [
                    {
                        "Patients": "Training members",
                        "Mean nearest distance": attack_result["train_distance_mean"],
                        "Median nearest distance": attack_result["train_distance_median"],
                    },
                    {
                        "Patients": "Held-out non-members",
                        "Mean nearest distance": attack_result["holdout_distance_mean"],
                        "Median nearest distance": attack_result["holdout_distance_median"],
                    },
                ]
            )
            st.dataframe(distance_metrics.round(3), use_container_width=True, hide_index=True)
            chart_col, roc_col = st.columns(2)
            with chart_col:
                st.plotly_chart(_privacy_distance_chart(attack_result), use_container_width=True)
            with roc_col:
                st.plotly_chart(_privacy_roc_chart(attack_result), use_container_width=True)
            st.write(attack_result["interpretation"])
            st.caption(
                "Lower nearest-neighbor distance makes a patient more likely to be classified as a training member. "
                "This result applies only to this simulated threat model. "
                + attack_result["threshold_method"]
            )
            st.caption(attack_result["warning"])
    st.caption("Diagnostic result; not a guarantee of anonymization, HIPAA compliance, or privacy.")

    st.markdown("### 5. Population shift")
    achievement = _actual_proportions(generated, request) if request else pd.DataFrame()
    if not achievement.empty:
        display = achievement.rename(
            columns={
                "Source target %": "Requested target",
                "Deviation (Δ)": "Deviation",
            }
        )
        if "Deviation" not in display.columns and {"Requested target", "Generated %"} <= set(display.columns):
            display["Deviation"] = (
                    pd.to_numeric(display["Generated %"], errors="coerce")
                    - pd.to_numeric(display["Requested target"], errors="coerce")
            ).abs()
        keep = [c for c in ("Variable", "Requested target", "Generated %", "Deviation") if c in display.columns]
        st.dataframe(display.loc[:, keep] if keep else display, use_container_width=True, hide_index=True)
    else:
        st.caption("Population-shift diagnostics are unavailable.")
    st.caption(
        "Target achievement measures the generated cohort against the requested specification; "
        "it does not establish clinical validity."
    )

    tstr = validation.get("tstr", {}) if isinstance(validation, Mapping) else {}
    st.markdown("### 6. Task-specific utility")
    if isinstance(tstr, Mapping) and tstr.get("status") == "ok":
        st.dataframe(_tstr_display_table(tstr), use_container_width=True, hide_index=True)
        st.caption("TSTR is task-specific utility evidence, not clinical validation.")
    else:
        st.caption("Task-specific utility has not been computed or is unavailable.")

    st.markdown("### 7. Model comparison")
    st.caption(
        "Measured evidence from the same patient-level training partition. "
        "This comparison does not select a universally superior synthesis method."
    )

    comparison_result = st.session_state.model_comparison_output

    if st.button(
            "Run model comparison",
            type="secondary",
            key="run_model_comparison",
    ):
        with st.spinner(
                "Running controlled Gaussian Copula and CTGAN comparison..."
        ):
            st.session_state.model_comparison_output = _model_comparison(
                source, request
            )
        comparison_result = st.session_state.model_comparison_output

    if isinstance(comparison_result, Mapping):
        if comparison_result.get("status") not in {"ok", "OK"}:
            if comparison_result.get("error"):
                st.warning(
                    f"Model comparison unavailable: "
                    f"{comparison_result['error']}"
                )
        else:
            results = comparison_result.get("results", [])

            if results:
                rows = []

                for result in results:
                    rows.append(
                        {
                            "Model": result.get("model", "Unavailable"),
                            "Generation time (s)": result.get(
                                "generation_seconds"
                            ),
                            "Records": result.get("n_records"),
                            "Quality diagnostic": result.get(
                                "quality_score"
                            ),
                            "Mean correlation difference": result.get(
                                "mean_correlation_difference"
                            ),
                            "Mean missingness difference": result.get(
                                "mean_missingness_difference"
                            ),
                            "Target deviation": result.get(
                                "target_deviation"
                            ),
                            "Privacy status": (
                                "Measured"
                                if result.get("privacy_attack_auroc")
                                   is not None
                                else result.get(
                                    "privacy_note", "Not run"
                                )
                            ),
                        }
                    )

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )

                train_patients = comparison_result.get("train_patients")

                if train_patients is not None:
                    st.caption(
                        f"Common training partition: {train_patients:,} patients. "
                        "Evidence comparison only; no winner or ranking is selected."
                    )
            else:
                st.info("No model comparison results are available.")

    time_col = next((c for c in source.columns if c.lower() in {"month", "date", "time", "timestamp"}), None)
    generation = _import_optional("backend.generation")
    longitudinal_fn = getattr(generation, "generate_longitudinal", None) if generation else None
    if time_col and longitudinal_fn:
        st.markdown("### 8. Longitudinal explorer")
        st.caption(
            "Trajectory bootstrap resamples observed longitudinal change patterns; "
            "it does not mechanistically model disease progression."
        )
        trajectory_options = [
            column
            for column in ("systolic_bp", "medication_adherence_pct", "pain_score", "activity_steps")
            if column in source.columns and column in generated.columns
        ]
        if trajectory_options:
            control_col, action_col = st.columns([2, 1], gap="small")
            with control_col:
                trajectory_col = st.selectbox(
                    "Trajectory variable",
                    trajectory_options,
                    key="trajectory_variable",
                )
            with action_col:
                st.markdown("<div style='height: 1.55rem'></div>", unsafe_allow_html=True)
                build_trajectory = st.button(
                    "Build trajectory comparison",
                    type="secondary",
                    use_container_width=True,
                )
            if build_trajectory:
                try:
                    patient_col = next(
                        (c for c in generated.columns if "patient" in c.lower() and "id" in c.lower()),
                        generated.columns[0],
                    )
                    if time_col in generated.columns:
                        baseline = generated.sort_values(time_col).groupby(patient_col, as_index=False).first()
                    else:
                        baseline = generated.groupby(patient_col, as_index=False).first()
                    st.session_state.longitudinal_df = longitudinal_fn(source, baseline, time_col)
                except Exception as exc:
                    st.warning(f"Longitudinal explorer unavailable: {exc}")
            longitudinal = st.session_state.longitudinal_df
            if longitudinal is not None:
                real_line = _trajectory_summary(source, time_col, trajectory_col, "Source")
                synthetic_line = _trajectory_summary(longitudinal, time_col, trajectory_col, "Synthetic")
                title = (
                    "Average systolic BP over time"
                    if trajectory_col == "systolic_bp"
                    else f"Average {trajectory_col.replace('_', ' ')} over time"
                )
                trajectory_fig = px.line(
                    pd.concat([real_line, synthetic_line], ignore_index=True),
                    x=time_col,
                    y=trajectory_col,
                    color="dataset",
                    markers=True,
                    title=title,
                    labels={"dataset": "", trajectory_col: trajectory_col.replace("_", " ").title()},
                    color_discrete_map={"Source": PALETTE["navy"], "Synthetic": PALETTE["blue"]},
                    template="plotly_white",
                )
                trajectory_fig.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=48, b=10),
                    legend=dict(orientation="h", y=1.12, x=0),
                    paper_bgcolor="#fbfcfd",
                    plot_bgcolor="#ffffff",
                )
                st.plotly_chart(trajectory_fig, use_container_width=True)
                st.caption("Group-level mean trajectory; individual patient trajectories may vary.")
    _next_button(7)


def _page_export() -> None:
    generated = st.session_state.generated_df
    if generated is None:
        st.warning("Generate a cohort first.")
        return
    st.markdown('<div class="section-kicker">08 / export</div>', unsafe_allow_html=True)
    st.title("Export research cohort")
    c1, c2, c3, c4 = st.columns(4, gap="small")
    feasibility = _metric_from_mapping(
        st.session_state.feasibility_output,
        ("overall", "status"),
        "Unavailable",
    )
    validation_status = "Complete" if st.session_state.validation_output else "Unavailable"
    feasibility_display = (
        f"{feasibility} / confirmed"
        if str(feasibility).lower() == "sparse" and st.session_state.sparse_confirmed
        else feasibility
    )
    used_model = st.session_state.generation_model_used or st.session_state.selected_generation_model
    for col, label, value in (
            (c1, "Generated records", f"{len(generated):,}"),
            (c2, "Model", _model_label(used_model)),
            (c3, "Feasibility", feasibility_display),
            (c4, "Validation", validation_status),
    ):
        with col:
            _metric(label, value)
    csv = generated.to_csv(index=False).encode("utf-8")
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        generated.to_excel(writer, index=False, sheet_name="synthetic_cohort")
    download_col1, download_col2, download_col3 = st.columns(3, gap="small")
    with download_col1:
        st.download_button(
            "Download CSV",
            csv,
            "medsyn_synthetic_cohort.csv",
            "text/csv",
            type="primary",
            use_container_width=True,
        )
    with download_col2:
        st.download_button(
            "Download Excel",
            excel_buffer.getvalue(),
            "medsyn_synthetic_cohort.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
            use_container_width=True,
        )
    report = json.dumps(
        {
            "cohort_request": st.session_state.cohort_request,
            "feasibility": st.session_state.feasibility_output,
            "sanity": st.session_state.sanity_output,
            "validation": st.session_state.validation_output,
            "privacy_attack": st.session_state.privacy_attack_output,
            "model_comparison": st.session_state.model_comparison_output,
        },
        default=str,
        indent=2,
    ).encode("utf-8")
    with download_col3:
        st.download_button(
            "Download Validation Report",
            report,
            "medsyn_validation_report.json",
            "application/json",
            type="secondary",
            use_container_width=True,
        )


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
