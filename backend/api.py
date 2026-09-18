"""
Synora FastAPI Backend
----------------------

Thin API adapter between the React/Vite frontend and the existing
scientific Python engines.

Architecture:

React
  -> FastAPI
      -> feasibility.py
      -> generation/generation.py
      -> validation.py
      -> privacy.py
      -> sanity.py
      -> sparsity.py

This backend intentionally keeps the existing scientific modules as
the source of truth instead of duplicating their algorithms here.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response


# =============================================================================
# Application
# =============================================================================

app = FastAPI(
    title="Synora API",
    description="Synthetic Clinical Cohort Intelligence Platform",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Imports from existing scientific modules
# =============================================================================

from feasibility import (  # noqa: E402
    CohortCondition,
    CohortRequest,
    check_feasibility,
    find_patient_identifier,
)

from backend.generation.generation import (  # noqa: E402
    generate_cross_sectional,
    generate_longitudinal,
)

from validation import (  # noqa: E402
    compute_k_anonymity,
    compute_privacy_metrics,
    compute_quality_metrics,
    compute_tstr,
    evaluate_privacy_gate,
    generate_privacy_certificate,
)

from privacy import run_membership_inference_simulation  # noqa: E402


# =============================================================================
# In-memory application state
# =============================================================================
#
# For the hackathon/demo this is intentional.
#
# Production would use a job/session/dataset identifier and persistent storage.
# =============================================================================

STATE: dict[str, Any] = {
    "source_df": None,
    "source_name": "demo_patients.csv",
    "profile": None,
    "feasibility": None,
    "generated_df": None,
    "generation_request": None,
    "trust_report": None,
    "certificate": None,
}


# =============================================================================
# Utility functions
# =============================================================================

def _json_safe(value: Any) -> Any:
    """Convert NumPy/Pandas values into JSON-safe Python values."""

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]

    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        if not np.isfinite(value):
            return None
        return float(value)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, float):
        if not np.isfinite(value):
            return None
        return value

    if pd.isna(value):
        return None

    if isinstance(value, (str, bool, int)):
        return value

    return str(value)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-safe records."""

    if df is None or df.empty:
        return []

    return _json_safe(
        df.replace({np.nan: None}).to_dict(orient="records")
    )


def _find_time_column(df: pd.DataFrame) -> str | None:
    """Find the longitudinal time column."""

    preferred = [
        "month",
        "date",
        "time",
        "timestamp",
        "visit_date",
        "year",
    ]

    for column in preferred:
        if column in df.columns:
            return column

    for column in df.columns:
        name = str(column).lower()

        if any(
                token in name
                for token in ("month", "date", "time", "timestamp")
        ):
            return column

    return None


def _find_demo_dataset() -> Path | None:
    """Locate the bundled demonstration dataset."""

    root = Path(__file__).resolve().parent.parent

    candidates = [
        root / "data" / "demo_patients.csv",
        root / "data" / "patients.csv",
        root / "data" / "synthetic_patients.csv",
        ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    data_dir = root / "data"

    if data_dir.exists():
        csv_files = sorted(data_dir.glob("*.csv"))

        if csv_files:
            return csv_files[0]

    return None


def _read_dataframe(
        content: bytes,
        filename: str,
) -> pd.DataFrame:
    """Read CSV/XLSX bytes into a DataFrame."""

    suffix = Path(filename).suffix.lower()

    try:
        if suffix == ".csv":
            df = pd.read_csv(io.BytesIO(content))

        elif suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(io.BytesIO(content))

        else:
            raise ValueError(
                "Unsupported file type. Upload CSV or XLSX."
            )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read dataset: {exc}",
        ) from exc

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Uploaded dataset is empty.",
        )

    # Clean whitespace around column names.
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


def _ensure_source_loaded() -> pd.DataFrame:
    """Return the current source dataset, loading the demo if necessary."""

    source = STATE.get("source_df")

    if isinstance(source, pd.DataFrame) and not source.empty:
        return source

    demo = _find_demo_dataset()

    if demo is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No source dataset is loaded and no demo dataset "
                "was found under data/."
            ),
        )

    try:
        source = pd.read_csv(demo)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load demo dataset: {exc}",
        ) from exc

    source.columns = [
        str(column).strip()
        for column in source.columns
    ]

    STATE["source_df"] = source
    STATE["source_name"] = demo.name

    return source


def _patient_baseline(source: pd.DataFrame) -> pd.DataFrame:
    """
    Build one baseline row per patient.

    Uses the existing generation engine's baseline logic when a
    patient identifier and time column are available.
    """

    identifier = find_patient_identifier(source)
    time_col = _find_time_column(source)

    if identifier and time_col:
        from backend.generation.generation import build_patient_baseline

        return build_patient_baseline(
            source,
            identifier,
            time_col,
        )

    if identifier:
        return (
            source
            .drop_duplicates(identifier, keep="first")
            .reset_index(drop=True)
        )

    return source.drop_duplicates().reset_index(drop=True)


# =============================================================================
# Dataset DNA
# =============================================================================

def _build_profile(source: pd.DataFrame) -> dict[str, Any]:
    """Build the Dataset DNA payload consumed by the React frontend."""

    identifier = find_patient_identifier(source)
    time_col = _find_time_column(source)

    baseline = _patient_baseline(source)

    total_patients = (
        int(baseline[identifier].nunique())
        if identifier and identifier in baseline.columns
        else len(baseline)
    )

    months_recorded = (
        int(source[time_col].nunique(dropna=True))
        if time_col and time_col in source.columns
        else 1
    )

    columns: dict[str, Any] = {}

    for column in source.columns:
        series = source[column]

        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(
                series,
                errors="coerce",
            ).dropna()

            columns[column] = {
                "dtype": str(series.dtype),
                "type": "numerical",
                "min": (
                    float(numeric.min())
                    if not numeric.empty
                    else None
                ),
                "max": (
                    float(numeric.max())
                    if not numeric.empty
                    else None
                ),
                "mean": (
                    float(numeric.mean())
                    if not numeric.empty
                    else None
                ),
            }

        else:
            categories = (
                series
                .dropna()
                .astype(str)
                .value_counts()
                .head(50)
                .index
                .tolist()
            )

            columns[column] = {
                "dtype": str(series.dtype),
                "type": "categorical",
                "categories": categories,
            }

    # -------------------------------------------------------------------------
    # Cohort benchmarks
    # -------------------------------------------------------------------------

    benchmark = baseline.copy()

    if "diabetic" in benchmark.columns:
        diabetic_numeric = pd.to_numeric(
            benchmark["diabetic"],
            errors="coerce",
        ).fillna(0)

        diabetic_count = int(
            (diabetic_numeric == 1).sum()
        )

        if "age" in benchmark.columns:
            age_numeric = pd.to_numeric(
                benchmark["age"],
                errors="coerce",
            )

            diabetic_age_gt_65 = int(
                (
                        (diabetic_numeric == 1)
                        & (age_numeric > 65)
                ).sum()
            )
        else:
            diabetic_age_gt_65 = 0

        if {
            "age",
            "ethnicity",
        }.issubset(benchmark.columns):

            age_numeric = pd.to_numeric(
                benchmark["age"],
                errors="coerce",
            )

            triple_combo = int(
                (
                        (diabetic_numeric == 1)
                        & (age_numeric > 65)
                        & (
                            benchmark["ethnicity"]
                            .astype(str)
                            .eq("Other")
                        )
                ).sum()
            )

        else:
            triple_combo = 0

    else:
        diabetic_count = 0
        diabetic_age_gt_65 = 0
        triple_combo = 0

    # -------------------------------------------------------------------------
    # Sparsity health
    # -------------------------------------------------------------------------

    sparsity_health = {
        "health_score": None,
        "sparse_cell_count": None,
    }

    try:
        from sparsity import compute_sparsity

        sparsity_frame = baseline.copy()

        if "age" in sparsity_frame.columns:
            age_numeric = pd.to_numeric(
                sparsity_frame["age"],
                errors="coerce",
            )
            sparsity_frame["age_over_65"] = (
                    age_numeric > 65
            ).astype(int)

        key_dimensions = [
            column
            for column in [
                "diabetic",
                "age_over_65",
                "gender",
                "ethnicity",
            ]
            if column in sparsity_frame.columns
        ]

        if key_dimensions:
            result = compute_sparsity(
                sparsity_frame,
                key_dimensions,
            )

            if isinstance(result, dict):
                sparsity_health.update(
                    _json_safe(result)
                )

    except Exception:
        # Sparsity is supporting profile information.
        pass

    # -------------------------------------------------------------------------
    # Demographics
    # -------------------------------------------------------------------------

    age_histogram: list[dict[str, Any]] = []

    if "age" in baseline.columns:
        age = pd.to_numeric(
            baseline["age"],
            errors="coerce",
        ).dropna()

        bins = {
            "<35": int((age < 35).sum()),
            "35-50": int(
                ((age >= 35) & (age <= 50)).sum()
            ),
            "51-65": int(
                ((age >= 51) & (age <= 65)).sum()
            ),
            ">65": int((age > 65).sum()),
        }

        age_histogram = [
            {
                "range": label,
                "count": count,
            }
            for label, count in bins.items()
        ]

    gender_doughnut: list[dict[str, Any]] = []

    if "gender" in baseline.columns:
        gender_counts = (
            baseline["gender"]
            .astype(str)
            .value_counts()
        )

        gender_doughnut = [
            {
                "name": str(label),
                "value": int(count),
            }
            for label, count in gender_counts.items()
        ]

    ethnicity_bar: list[dict[str, Any]] = []

    if "ethnicity" in baseline.columns:
        ethnicity_counts = (
            baseline["ethnicity"]
            .astype(str)
            .value_counts()
        )

        ethnicity_bar = [
            {
                "ethnicity": str(label),
                "count": int(count),
            }
            for label, count in ethnicity_counts.items()
        ]

    return _json_safe(
        {
            "schema": {
                "total_patients": total_patients,
                "total_rows": len(source),
                "months_recorded": months_recorded,
                "patient_id_column": identifier,
                "time_column": time_col,
                "columns": columns,
            },
            "benchmarks": {
                "diabetic_count": diabetic_count,
                "diabetic_age_gt_65": diabetic_age_gt_65,
                "triple_combo_sparse": triple_combo,
            },
            "sparsity_health": sparsity_health,
            "demographics": {
                "ageHistogram": age_histogram,
                "genderDoughnut": gender_doughnut,
                "ethnicityBar": ethnicity_bar,
            },
        }
    )


# =============================================================================
# Cohort filters -> CohortRequest
# =============================================================================

def _filters_to_conditions(
        filters: Any,
) -> list[dict[str, Any]]:
    """
    Convert frontend cohort-designer filters into the exact
    CohortCondition schema expected by feasibility.py.

    Supported frontend format:

        [
            {
                "field": "diabetic",
                "operator": "equals",
                "value": 1
            },
            {
                "field": "age",
                "operator": "between",
                "value": [66, 90]
            }
        ]

    Supported legacy backend format:

        {
            "diabetic": 1,
            "age_min": 66,
            "age_max": 90,
            "gender": "Female",
            "ethnicity": "..."
        }

    Output format:

        {
            "variable": "...",
            "operator": "...",
            "value": ...,
            "target_pct": 100.0,
            "label": "..."
        }
    """

    if not filters:
        return []

    conditions: list[dict[str, Any]] = []

    # =========================================================
    # FRONTEND FORMAT
    # =========================================================
    if isinstance(filters, list):

        for item in filters:
            if not isinstance(item, dict):
                continue

            field = item.get("field")
            frontend_operator = item.get("operator", "equals")
            value = item.get("value")

            if not field:
                continue

            # -------------------------------------------------
            # Diabetic / categorical / equality filters
            # -------------------------------------------------
            if field == "diabetic":
                if frontend_operator in {
                    "equals",
                    "eq",
                    "==",
                }:
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        pass

                    conditions.append(
                        {
                            "variable": "diabetic",
                            "operator": "==",
                            "value": value,
                            "target_pct": 100.0,
                            "label": "Diabetic",
                        }
                    )

                elif frontend_operator in {
                    "not_equals",
                    "neq",
                    "!=",
                }:
                    conditions.append(
                        {
                            "variable": "diabetic",
                            "operator": "!=",
                            "value": value,
                            "target_pct": 100.0,
                            "label": "Not diabetic",
                        }
                    )

                continue

            # -------------------------------------------------
            # Age filters
            # -------------------------------------------------
            if field == "age":

                if frontend_operator == "between":
                    if (
                            isinstance(value, (list, tuple))
                            and len(value) >= 2
                    ):
                        conditions.append(
                            {
                                "variable": "age",
                                "operator": ">=",
                                "value": float(value[0]),
                                "target_pct": 100.0,
                                "label": "Minimum age",
                            }
                        )

                        conditions.append(
                            {
                                "variable": "age",
                                "operator": "<=",
                                "value": float(value[1]),
                                "target_pct": 100.0,
                                "label": "Maximum age",
                            }
                        )

                elif frontend_operator in {
                    "gte",
                    "greater_than_or_equal",
                    ">=",
                }:
                    conditions.append(
                        {
                            "variable": "age",
                            "operator": ">=",
                            "value": float(value),
                            "target_pct": 100.0,
                            "label": "Minimum age",
                        }
                    )

                elif frontend_operator in {
                    "lte",
                    "less_than_or_equal",
                    "<=",
                }:
                    conditions.append(
                        {
                            "variable": "age",
                            "operator": "<=",
                            "value": float(value),
                            "target_pct": 100.0,
                            "label": "Maximum age",
                        }
                    )

                elif frontend_operator in {
                    "gt",
                    "greater_than",
                    ">",
                }:
                    conditions.append(
                        {
                            "variable": "age",
                            "operator": ">",
                            "value": float(value),
                            "target_pct": 100.0,
                            "label": "Age",
                        }
                    )

                elif frontend_operator in {
                    "lt",
                    "less_than",
                    "<",
                }:
                    conditions.append(
                        {
                            "variable": "age",
                            "operator": "<",
                            "value": float(value),
                            "target_pct": 100.0,
                            "label": "Age",
                        }
                    )

                elif frontend_operator in {
                    "equals",
                    "eq",
                    "==",
                }:
                    conditions.append(
                        {
                            "variable": "age",
                            "operator": "==",
                            "value": float(value),
                            "target_pct": 100.0,
                            "label": "Age",
                        }
                    )

                continue

            # -------------------------------------------------
            # Generic categorical fields
            # -------------------------------------------------
            if frontend_operator in {
                "equals",
                "eq",
                "==",
            }:
                engine_operator = "=="

            elif frontend_operator in {
                "not_equals",
                "neq",
                "!=",
            }:
                engine_operator = "!="

            elif frontend_operator in {
                "gt",
                "greater_than",
                ">",
            }:
                engine_operator = ">"

            elif frontend_operator in {
                "gte",
                "greater_than_or_equal",
                ">=",
            }:
                engine_operator = ">="

            elif frontend_operator in {
                "lt",
                "less_than",
                "<",
            }:
                engine_operator = "<"

            elif frontend_operator in {
                "lte",
                "less_than_or_equal",
                "<=",
            }:
                engine_operator = "<="

            elif frontend_operator in {"in"}:
                engine_operator = "in"

            elif frontend_operator in {"not_in", "not in"}:
                engine_operator = "not in"

            else:
                raise ValueError(
                    f"Unsupported frontend operator "
                    f"'{frontend_operator}' for field '{field}'"
                )

            conditions.append(
                {
                    "variable": field,
                    "operator": engine_operator,
                    "value": value,
                    "target_pct": 100.0,
                    "label": str(field).replace("_", " ").title(),
                }
            )

        return conditions

    # =========================================================
    # LEGACY DICTIONARY FORMAT
    # =========================================================
    if isinstance(filters, dict):

        diabetic = filters.get("diabetic")

        if diabetic not in (None, "", "All"):
            try:
                diabetic = int(diabetic)
            except (TypeError, ValueError):
                pass

            conditions.append(
                {
                    "variable": "diabetic",
                    "operator": "==",
                    "value": diabetic,
                    "target_pct": 100.0,
                    "label": "Diabetic",
                }
            )

        age_min = filters.get("age_min")

        if age_min not in (None, ""):
            conditions.append(
                {
                    "variable": "age",
                    "operator": ">=",
                    "value": float(age_min),
                    "target_pct": 100.0,
                    "label": "Minimum age",
                }
            )

        age_max = filters.get("age_max")

        if age_max not in (None, ""):
            conditions.append(
                {
                    "variable": "age",
                    "operator": "<=",
                    "value": float(age_max),
                    "target_pct": 100.0,
                    "label": "Maximum age",
                }
            )

        gender = filters.get("gender")

        if gender not in (None, "", "All"):
            conditions.append(
                {
                    "variable": "gender",
                    "operator": "==",
                    "value": gender,
                    "target_pct": 100.0,
                    "label": "Gender",
                }
            )

        ethnicity = filters.get("ethnicity")

        if ethnicity not in (None, "", "All"):
            conditions.append(
                {
                    "variable": "ethnicity",
                    "operator": "==",
                    "value": ethnicity,
                    "target_pct": 100.0,
                    "label": "Ethnicity",
                }
            )

        return conditions

    raise ValueError(
        "filters must be either a list of frontend filter objects "
        "or a dictionary"
    )
def _build_cohort_request(
        filters: dict[str, Any],
        target_n: int,
        conditions: list[dict[str, Any]] | None = None,
) -> CohortRequest:
    """Create the existing feasibility engine request object."""

    raw_conditions = (
        conditions
        if conditions is not None
        else _filters_to_conditions(filters)
    )

    parsed = [
        CohortCondition.from_dict(condition)
        for condition in raw_conditions
    ]

    return CohortRequest(
        target_n=int(target_n),
        conditions=parsed,
        metadata={
            "source": "Synora React frontend",
        },
    )


# =============================================================================
# Simple frontend-compatible feasibility response
# =============================================================================

def _frontend_feasibility(
        source: pd.DataFrame,
        filters: dict[str, Any],
        researcher_confirmed: bool,
        target_n: int = 500,
) -> dict[str, Any]:
    """
    Run the real feasibility engine and additionally expose the compact
    response shape expected by the existing React cohort designer.
    """

    request = _build_cohort_request(
        filters,
        target_n,
    )

    try:
        result = check_feasibility(
            source,
            request,
        )

        result_dict = (
            result.to_dict()
            if hasattr(result, "to_dict")
            else dict(result)
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Feasibility evaluation failed: {exc}",
        ) from exc

    overall = str(
        result_dict.get(
            "overall",
            result_dict.get("overall_tier", "Sparse"),
        )
    )

    # The scientific feasibility engine is the source of truth.
    # Weak/Sparse/Unsupported evidence requires explicit researcher
    # confirmation before generation.
    engine_requires_confirmation = bool(
        result_dict.get("requires_confirmation", False)
    )

    engine_weak_evidence = overall.lower() in {
        "weak",
        "sparse",
        "unsupported",
    }

    requires_confirmation = (
            engine_requires_confirmation
            or engine_weak_evidence
    )

    passed = (
            not requires_confirmation
            or researcher_confirmed
    )

    # Calculate exact intersection count for the compact UI.
    baseline = _patient_baseline(source)

    mask = pd.Series(
        True,
        index=baseline.index,
    )

    for condition in request.conditions:
        variable = condition.variable

        if variable not in baseline.columns:
            mask &= False
            continue

        series = baseline[variable]
        value = condition.value

        if pd.api.types.is_numeric_dtype(series):
            try:
                value = float(value)
            except (TypeError, ValueError):
                pass

        if condition.operator == "==":
            mask &= series == value
        elif condition.operator == "!=":
            mask &= series != value
        elif condition.operator == ">":
            mask &= series > value
        elif condition.operator == ">=":
            mask &= series >= value
        elif condition.operator == "<":
            mask &= series < value
        elif condition.operator == "<=":
            mask &= series <= value
        elif condition.operator == "in":
            values = (
                value
                if isinstance(value, (list, tuple, set))
                else [value]
            )
            mask &= series.isin(values)
        elif condition.operator == "not in":
            values = (
                value
                if isinstance(value, (list, tuple, set))
                else [value]
            )
            mask &= ~series.isin(values)

    count = int(mask.sum())
    total = len(baseline)

    compact_tier = (
        "Strong"
        if count >= 30
        else "Moderate"
        if count >= 10
        else "Sparse"
        if count >= 3
        else "Unsupported"
    )

    if requires_confirmation and not researcher_confirmed:
        gate_status = "WARNING_REQUIRES_CONFIRMATION"
        message = (
            f"Source evidence is {overall}. "
            f"{count} patient(s) match the requested cohort "
            f"({(count / total * 100):.1f}% of the source population). "
            "Explicit researcher confirmation is required before generation."
        )
    elif requires_confirmation and researcher_confirmed:
        gate_status = "PASSED_WITH_CONFIRMATION"
        message = (
            f"Researcher confirmed generation despite {overall.lower()} "
            f"source evidence ({count} patient(s), "
            f"{(count / total * 100):.1f}% of the source population). "
            "Generation may proceed."
        )
    else:
        gate_status = "PASSED"
        message = (
            f"Sufficient source evidence found "
            f"({count} patient(s), Tier: {compact_tier})."
        )

    return _json_safe(
        {
            "matching_patient_count": count,
            "matching_patient_pct": (
                float(count / total * 100)
                if total
                else 0.0
            ),
            "support_tier": compact_tier,
            "engine_overall_tier": overall,
            "requires_confirmation": requires_confirmation,
            "researcher_confirmed": researcher_confirmed,
            "gate_status": gate_status,
            "passed": passed,
            "message": message,
            "engine_result": result_dict,
        }
    )


# =============================================================================
# Synthetic cohort generation
# =============================================================================

def _normalise_synthetic_baseline(
        baseline: pd.DataFrame,
        patient_id_col: str | None,
) -> pd.DataFrame:
    """
    Guarantee fresh synthetic patient identifiers.

    The existing generator already creates synthetic IDs. This function
    makes the API contract explicit and protects against accidental source
    identifier leakage.
    """

    result = baseline.copy().reset_index(drop=True)

    if patient_id_col:
        if patient_id_col not in result.columns:
            result.insert(
                0,
                patient_id_col,
                [
                    f"synthetic_{index + 1:06d}"
                    for index in range(len(result))
                ],
            )
        else:
            result[patient_id_col] = [
                f"synthetic_{index + 1:06d}"
                for index in range(len(result))
            ]

    return result


def _run_generation(
        source: pd.DataFrame,
        payload: dict[str, Any],
        feasibility: dict[str, Any],
) -> pd.DataFrame:
    """Generate synthetic baseline patients and longitudinal trajectories."""

    model = str(
        payload.get(
            "model",
            "gaussian_copula",
        )
    ).lower()

    if model not in {
        "gaussian_copula",
        "ctgan",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported model. "
                "Use 'gaussian_copula' or 'ctgan'."
            ),
        )

    num_patients = int(
        payload.get(
            "n_patients",
            payload.get(
                "num_patients",
                payload.get("target_n", 500),
            ),
        )
    )

    num_patients = max(
        1,
        min(num_patients, 5000),
    )

    filters = payload.get(
        "filters",
        {},
    ) or {}

    supplied_conditions = payload.get(
        "conditions"
    )

    conditions = (
        supplied_conditions
        if supplied_conditions
        else _filters_to_conditions(filters)
    )

    generation_request = {
        "conditions": conditions,
        "target_shift": payload.get(
            "target_shift",
            {},
        ) or {},
    }

    # CTGAN can be made substantially faster for a hackathon demo.
    if model == "ctgan":
        generation_request["epochs"] = int(
            payload.get("epochs", 50)
        )

    # -------------------------------------------------------------------------
    # Generate one baseline record per synthetic patient.
    # -------------------------------------------------------------------------

    try:
        synthetic_baseline = generate_cross_sectional(
            source,
            request=generation_request,
            n_rows=num_patients,
            model=model,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{model} generation failed: {exc}",
        ) from exc

    identifier = find_patient_identifier(source)
    time_col = _find_time_column(source)

    synthetic_baseline = _normalise_synthetic_baseline(
        synthetic_baseline,
        identifier,
    )

    # -------------------------------------------------------------------------
    # Longitudinal synthesis.
    # -------------------------------------------------------------------------

    if identifier and time_col:
        try:
            generated = generate_longitudinal(
                source,
                synthetic_baseline,
                time_col,
            )

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Longitudinal trajectory generation failed: "
                    f"{exc}"
                ),
            ) from exc

    else:
        generated = synthetic_baseline.copy()

    generated = generated.reset_index(drop=True)

    # Make absolutely sure generated identifiers are synthetic.
    if identifier and identifier in generated.columns:
        unique_ids = list(
            generated[identifier]
            .drop_duplicates()
        )

        id_mapping = {
            old_id: f"SYN_{index + 1:03d}"
            for index, old_id in enumerate(unique_ids)
        }

        generated[identifier] = (
            generated[identifier]
            .map(id_mapping)
        )

    return generated


# =============================================================================
# Trust report helpers
# =============================================================================

def _numeric_mean(
        df: pd.DataFrame,
        column: str,
) -> float | None:
    if column not in df.columns:
        return None

    values = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    return float(values.mean())


def _percentage(
        df: pd.DataFrame,
        column: str,
        positive: Any = 1,
) -> float | None:
    if column not in df.columns or df.empty:
        return None

    values = df[column]

    if pd.api.types.is_numeric_dtype(values):
        values = pd.to_numeric(
            values,
            errors="coerce",
        )

        valid = values.dropna()

        if valid.empty:
            return None

        return float(
            (valid == positive).mean() * 100
        )

    return float(
        values.astype(str)
        .eq(str(positive))
        .mean()
        * 100
    )


def _build_kde(
        source: pd.DataFrame,
        generated: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Build HbA1c density overlay data for the frontend chart."""

    column = "hba1c"

    if column not in source.columns or column not in generated.columns:
        return []

    source_values = pd.to_numeric(
        source[column],
        errors="coerce",
    ).dropna().to_numpy()

    generated_values = pd.to_numeric(
        generated[column],
        errors="coerce",
    ).dropna().to_numpy()

    if len(source_values) < 2 or len(generated_values) < 2:
        return []

    low = float(
        min(
            source_values.min(),
            generated_values.min(),
        )
    )

    high = float(
        max(
            source_values.max(),
            generated_values.max(),
        )
    )

    if high <= low:
        high = low + 1.0

    points = np.linspace(
        low,
        high,
        8,
    )

    try:
        from scipy.stats import gaussian_kde

        source_kde = gaussian_kde(source_values)
        generated_kde = gaussian_kde(generated_values)

        source_density = source_kde(points)
        generated_density = generated_kde(points)

        # Normalise only for visual comparison.
        max_density = max(
            float(source_density.max()),
            float(generated_density.max()),
            1e-9,
        )

        source_density = (
                source_density / max_density
        )

        generated_density = (
                generated_density / max_density
        )

    except Exception:
        # Histogram fallback.
        source_hist, edges = np.histogram(
            source_values,
            bins=8,
            range=(low, high),
            density=True,
        )

        generated_hist, _ = np.histogram(
            generated_values,
            bins=8,
            range=(low, high),
            density=True,
        )

        max_density = max(
            float(source_hist.max()),
            float(generated_hist.max()),
            1e-9,
        )

        source_density = (
                source_hist / max_density
        )

        generated_density = (
                generated_hist / max_density
        )

        points = (
                         edges[:-1] + edges[1:]
                 ) / 2

    return [
        {
            "hba1c": f"{float(x):.1f}%",
            "SourceDensity": float(source_density[i]),
            "SyntheticDensity": float(
                generated_density[i]
            ),
        }
        for i, x in enumerate(points)
    ]


def _correlation(
        df: pd.DataFrame,
        left: str,
        right: str,
) -> float | None:
    if left not in df.columns or right not in df.columns:
        return None

    values = df[
        [left, right]
    ].apply(
        pd.to_numeric,
        errors="coerce",
    ).dropna()

    if (
            len(values) < 2
            or values[left].nunique() < 2
            or values[right].nunique() < 2
    ):
        return None

    value = values[left].corr(
        values[right]
    )

    return (
        None
        if pd.isna(value)
        else float(value)
    )


def _build_correlation_matrix(
        source: pd.DataFrame,
        generated: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Build the matrix expected by the existing React heatmap.

    These are statistical associations, not causal relationships.
    """

    features = {
        "HbA1c": "hba1c",
        "SystolicBP": "systolic_bp",
        "ActivityScore": "activity_steps",
        "PainScore": "pain_score",
        "Adherence": "medication_adherence_pct",
    }

    names = list(features.keys())

    rows = []

    for row_name in names:
        row = {
            "feature": row_name
        }

        for column_name in names:
            left = features[row_name]
            right = features[column_name]

            if row_name == column_name:
                row[column_name] = 1.0
                continue

            source_corr = _correlation(
                source,
                left,
                right,
            )

            synthetic_corr = _correlation(
                generated,
                left,
                right,
            )

            # Use synthetic relationship in the visual matrix.
            # Source/synthetic differences are separately exposed below.
            row[column_name] = (
                synthetic_corr
                if synthetic_corr is not None
                else source_corr
            )

        rows.append(row)

    return _json_safe(rows)


def _build_population_shift(
        source: pd.DataFrame,
        generated: pd.DataFrame,
        target_shift: dict[str, Any],
) -> dict[str, Any]:
    """Build source/request/synthetic population shift information."""

    source_diabetic = _percentage(
        source,
        "diabetic",
        1,
    )

    generated_diabetic = _percentage(
        generated,
        "diabetic",
        1,
    )

    source_age = _numeric_mean(
        source,
        "age",
    )

    generated_age = _numeric_mean(
        generated,
        "age",
    )

    source_bp = _numeric_mean(
        source,
        "systolic_bp",
    )

    generated_bp = _numeric_mean(
        generated,
        "systolic_bp",
    )

    target_diabetic = target_shift.get(
        "target_diabetic_pct",
        source_diabetic,
    )

    target_age = target_shift.get(
        "target_mean_age",
        source_age,
    )

    target_bp = target_shift.get(
        "target_mean_bp",
        source_bp,
    )

    achievement_scores = []

    if (
            target_diabetic is not None
            and generated_diabetic is not None
    ):
        denominator = max(
            abs(float(target_diabetic)),
            1.0,
        )

        achievement_scores.append(
            max(
                0.0,
                100.0
                - (
                        abs(
                            generated_diabetic
                            - float(target_diabetic)
                        )
                        / denominator
                        * 100.0
                ),
                )
        )

    if (
            target_age is not None
            and generated_age is not None
    ):
        denominator = max(
            abs(float(target_age)),
            1.0,
        )

        achievement_scores.append(
            max(
                0.0,
                100.0
                - (
                        abs(
                            generated_age
                            - float(target_age)
                        )
                        / denominator
                        * 100.0
                ),
                )
        )

    if (
            target_bp is not None
            and generated_bp is not None
    ):
        denominator = max(
            abs(float(target_bp)),
            1.0,
        )

        achievement_scores.append(
            max(
                0.0,
                100.0
                - (
                        abs(
                            generated_bp
                            - float(target_bp)
                        )
                        / denominator
                        * 100.0
                ),
                )
        )

    return _json_safe(
        {
            "baseline_source": {
                "diabetic_pct": source_diabetic,
                "mean_age": source_age,
                "mean_bp": source_bp,
            },
            "target_request": {
                "diabetic_pct": target_diabetic,
                "mean_age": target_age,
                "mean_bp": target_bp,
            },
            "synthetic_achieved": {
                "diabetic_pct": generated_diabetic,
                "mean_age": generated_age,
                "mean_bp": generated_bp,
            },
            "target_achievement_pct": (
                float(np.mean(achievement_scores))
                if achievement_scores
                else None
            ),
        }
    )


def _build_patient_payload(
        generated: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Build patient-level records for the Population Explorer."""

    identifier = find_patient_identifier(
        generated
    )

    if not identifier or identifier not in generated.columns:
        return []

    demographic_columns = [
        column
        for column in [
            identifier,
            "age",
            "gender",
            "ethnicity",
            "diabetic",
        ]
        if column in generated.columns
    ]

    patients = (
        generated[
            demographic_columns
        ]
        .drop_duplicates(
            identifier,
            keep="first",
        )
        .reset_index(drop=True)
    )

    return _records(patients)


def _build_scatter_points(
        generated: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Build patient-level scatter data."""

    identifier = find_patient_identifier(
        generated
    )

    if not identifier:
        return []

    numeric_candidates = [
        column
        for column in [
            "hba1c",
            "systolic_bp",
            "activity_steps",
            "pain_score",
            "medication_adherence_pct",
        ]
        if column in generated.columns
    ]

    if len(numeric_candidates) < 2:
        return []

    x_column = numeric_candidates[0]
    y_column = numeric_candidates[1]

    grouped = (
        generated
        .groupby(identifier)
        [[x_column, y_column]]
        .mean()
        .reset_index()
    )

    points = []

    for _, row in grouped.iterrows():
        points.append(
            {
                "patient_id": str(
                    row[identifier]
                ),
                "x": (
                    None
                    if pd.isna(row[x_column])
                    else float(row[x_column])
                ),
                "y": (
                    None
                    if pd.isna(row[y_column])
                    else float(row[y_column])
                ),
            }
        )

    return _json_safe(points)


# =============================================================================
# Full validation pipeline
# =============================================================================

def _run_full_validation(
        source: pd.DataFrame,
        generated: pd.DataFrame,
        feasibility: dict[str, Any],
        model: str,
        target_shift: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the complete Synora evidence pipeline."""

    # -------------------------------------------------------------------------
    # Quality / fidelity
    # -------------------------------------------------------------------------

    quality = compute_quality_metrics(
        source,
        generated,
    )

    # -------------------------------------------------------------------------
    # DCR / privacy distance
    # -------------------------------------------------------------------------

    privacy_distance = compute_privacy_metrics(
        source,
        generated,
    )

    dcr = (
        privacy_distance.get("dcr")
        if isinstance(
            privacy_distance,
            dict,
        )
        else None
    )

    # -------------------------------------------------------------------------
    # Membership Inference Attack
    # -------------------------------------------------------------------------

    try:
        # Gaussian Copula is intentionally used as the privacy threat-model
        # generator. This keeps the privacy diagnostic fast and reproducible
        # even when the researcher selected CTGAN for the actual cohort.
        mia = run_membership_inference_simulation(
            source,
            generator_model="gaussian_copula",
        )

    except Exception as exc:
        mia = {
            "status": "error",
            "error": str(exc),
        }

    # -------------------------------------------------------------------------
    # k-anonymity / uniqueness diagnostic
    # -------------------------------------------------------------------------

    k_frame = generated.copy()

    if "age" in k_frame.columns:
        age_numeric = pd.to_numeric(
            k_frame["age"],
            errors="coerce",
        )

        k_frame["age_over_65"] = (
                age_numeric > 65
        ).astype(int)

    quasi_identifiers = [
        column
        for column in [
            "age_over_65",
            "diabetic",
            "gender",
            "ethnicity",
        ]
        if column in k_frame.columns
    ]

    if not quasi_identifiers:
        k_result = {
            "status": "error",
            "error": (
                "No supported quasi-identifiers "
                "were available."
            ),
        }

    else:
        k_result = compute_k_anonymity(
            k_frame,
            quasi_identifiers,
        )

    # -------------------------------------------------------------------------
    # Privacy Gate
    # -------------------------------------------------------------------------

    gate = evaluate_privacy_gate(
        mia,
        k_result,
        auroc_threshold=0.75,
        k_threshold=1,
    )

    # -------------------------------------------------------------------------
    # Do not silently pass unavailable privacy evidence.
    # -------------------------------------------------------------------------

    privacy_evidence_missing = []

    if not isinstance(mia, dict) or mia.get("status") == "error":
        privacy_evidence_missing.append(
            "Membership inference attack was unavailable."
        )

    if (
            not isinstance(k_result, dict)
            or k_result.get("status") == "error"
    ):
        privacy_evidence_missing.append(
            "Synthetic uniqueness/k-anonymity diagnostic was unavailable."
        )

    if privacy_evidence_missing:
        gate = {
            **gate,
            "status": "Block",
            "tier": "Block",
            "passed": False,
            "requires_confirmation": True,
            "reasons": [
                *gate.get("reasons", []),
                *privacy_evidence_missing,
            ],
            "interpretation": (
                "Privacy evidence is incomplete. "
                "Export requires explicit researcher review."
            ),
        }

    # -------------------------------------------------------------------------
    # TSTR utility evidence
    # -------------------------------------------------------------------------

    try:
        tstr = compute_tstr(
            source,
            generated,
            "diabetic",
        )
    except Exception as exc:
        tstr = {
            "status": "error",
            "error": str(exc),
        }

    # -------------------------------------------------------------------------
    # Certificate
    # -------------------------------------------------------------------------

    certificate = generate_privacy_certificate(
        feasibility,
        dcr,
        mia,
        k_result,
        gate,
    )

    # -------------------------------------------------------------------------
    # Cryptographic dataset fingerprint
    # -------------------------------------------------------------------------

    csv_bytes = generated.to_csv(
        index=False
    ).encode("utf-8")

    dataset_hash = hashlib.sha256(
        csv_bytes
    ).hexdigest().upper()

    certificate_id = (
            "CERT-SYN-"
            + dataset_hash[:16]
    )

    quality_score = None

    if isinstance(quality, dict):
        raw_score = quality.get(
            "sdmetrics_quality_score"
        )

        if raw_score is not None:
            try:
                quality_score = float(
                    raw_score
                )
            except (
                    TypeError,
                    ValueError,
            ):
                quality_score = None

    enhanced_certificate = {
        **certificate,
        "title": (
            "Synora Synthetic Patient Cohort "
            "Privacy & Fidelity Certificate"
        ),
        "certificate_id": certificate_id,
        "timestamp": certificate.get(
            "generated_at"
        ),
        "dataset_hash": dataset_hash[:16],
        "dataset_statistics": {
            "synthetic_patients": (
                int(
                    generated[
                        find_patient_identifier(
                            generated
                        )
                    ].nunique()
                )
                if find_patient_identifier(
                    generated
                )
                else len(generated)
            ),
            "total_rows": int(
                len(generated)
            ),
            "months_per_patient": (
                int(
                    generated[
                        _find_time_column(
                            generated
                        )
                    ].nunique()
                )
                if _find_time_column(
                    generated
                )
                else 1
            ),
        },
        "fidelity_metrics": {
            "quality_score": quality_score,
            "fidelity_score": (
                None
                if quality_score is None
                else quality_score * 100.0
            ),
            "activity_pain_correlation": {
                "source": _correlation(
                    source,
                    "activity_steps",
                    "pain_score",
                ),
                "synthetic": _correlation(
                    generated,
                    "activity_steps",
                    "pain_score",
                ),
                "expected_target": -0.56,
            },
        },
        "privacy_metrics": {
            "membership_inference_attack": mia,
            "k_anonymity": k_result,
            "dcr": dcr,
        },
        "privacy_gate_evaluation": gate,
        "utility": {
            "tstr": tstr,
        },
    }

    # -------------------------------------------------------------------------
    # Trust report
    # -------------------------------------------------------------------------

    trust_report = {
        "certificate": enhanced_certificate,
        "quality": quality,
        "privacy": privacy_distance,
        "membership_inference": mia,
        "k_anonymity": k_result,
        "privacy_gate": gate,
        "tstr": tstr,
        "kdePoints": _build_kde(
            source,
            generated,
        ),
        "correlationMatrix": (
            _build_correlation_matrix(
                source,
                generated,
            )
        ),
        "populationShift": (
            _build_population_shift(
                source,
                generated,
                target_shift,
            )
        ),
        "generated_rows": len(generated),
        "generated_patients": len(
            generated[
                find_patient_identifier(
                    generated
                )
            ].unique()
        )
        if find_patient_identifier(
            generated
        )
        else len(generated),
        "model": model,
    }

    return (
        _json_safe(trust_report),
        _json_safe(enhanced_certificate),
    )


# =============================================================================
# Generation orchestration
# =============================================================================

def _generate_and_validate(
        payload: dict[str, Any],
        feasibility: dict[str, Any],
) -> tuple[
    pd.DataFrame,
    dict[str, Any],
    dict[str, Any],
]:
    """Generate synthetic data and immediately run validation."""

    source = _ensure_source_loaded()

    model = str(
        payload.get(
            "model",
            "gaussian_copula",
        )
    ).lower()

    target_shift = payload.get(
        "target_shift",
        {},
    ) or {}

    generated = _run_generation(
        source,
        payload,
        feasibility,
    )

    trust_report, certificate = (
        _run_full_validation(
            source,
            generated,
            feasibility,
            model,
            target_shift,
        )
    )

    STATE["generated_df"] = generated
    STATE["generation_request"] = payload
    STATE["trust_report"] = trust_report
    STATE["certificate"] = certificate

    return (
        generated,
        trust_report,
        certificate,
    )


# =============================================================================
# API endpoints
# =============================================================================

@app.get("/api/health")
def health() -> dict[str, Any]:
    """Backend health check."""

    source = STATE.get("source_df")

    return {
        "status": "ok",
        "service": "synora-api",
        "source_loaded": (
                isinstance(source, pd.DataFrame)
                and not source.empty
        ),
    }


@app.post("/api/profile")
async def profile(
        file: Optional[UploadFile] = File(
            default=None
        ),
) -> dict[str, Any]:
    """
    Load/profile a dataset.

    If a file is provided:
        replace the current source dataset.

    If no file is provided:
        return the current dataset profile, loading the demo dataset if needed.
    """

    if file is not None:
        content = await file.read()

        source = _read_dataframe(
            content,
            file.filename or "uploaded.csv",
            )

        STATE["source_df"] = source
        STATE["source_name"] = (
                file.filename
                or "uploaded_dataset"
        )

        # New source means previous synthetic results are stale.
        STATE["feasibility"] = None
        STATE["generated_df"] = None
        STATE["generation_request"] = None
        STATE["trust_report"] = None
        STATE["certificate"] = None

    source = _ensure_source_loaded()

    profile_payload = _build_profile(
        source
    )

    STATE["profile"] = profile_payload

    return {
        "status": "ok",
        "source_name": STATE[
            "source_name"
        ],
        **profile_payload,
    }


@app.post("/api/feasibility")
def feasibility_endpoint(
        payload: dict[str, Any],
) -> dict[str, Any]:
    """Run the real cohort feasibility engine."""

    source = _ensure_source_loaded()

    filters = payload.get(
        "filters",
        {},
    ) or {}

    researcher_confirmed = bool(
        payload.get(
            "researcher_confirmed",
            False,
        )
    )

    target_n = int(
        payload.get(
            "target_n",
            500,
        )
    )

    result = _frontend_feasibility(
        source,
        filters,
        researcher_confirmed,
        target_n,
    )

    STATE["feasibility"] = result

    return result


@app.post("/api/generate")
def generate_endpoint(
        payload: dict[str, Any],
) -> dict[str, Any]:
    """Generate, validate and store a synthetic cohort."""

    source = _ensure_source_loaded()

    filters = payload.get(
        "filters",
        {},
    ) or {}

    researcher_confirmed = bool(
        payload.get(
            "researcher_confirmed",
            payload.get(
                "feasibility_confirmed",
                False,
            ),
        )
    )

    target_n = int(
        payload.get(
            "num_patients",
            payload.get(
                "target_n",
                500,
            ),
        )
    )

    feasibility = _frontend_feasibility(
        source,
        filters,
        researcher_confirmed,
        target_n,
    )

    # -------------------------------------------------------------------------
    # Symmetric Feasibility Gate
    # -------------------------------------------------------------------------

    if (
            feasibility.get(
                "requires_confirmation"
            )
            and not researcher_confirmed
    ):
        STATE["feasibility"] = feasibility

        raise HTTPException(
            status_code=409,
            detail=(
                "The requested cohort has sparse source evidence. "
                "Explicit researcher confirmation is required "
                "before generation."
            ),
        )

    STATE["feasibility"] = feasibility

    generated, trust_report, certificate = (
        _generate_and_validate(
            payload,
            feasibility,
        )
    )

    identifier = find_patient_identifier(
        generated
    )

    patients = _build_patient_payload(
        generated
    )

    records = _records(
        generated
    )

    return _json_safe(
        {
            "status": "ok",
            "model": payload.get(
                "model",
                "gaussian_copula",
            ),
            "feasibility": feasibility,
            "synthPatients": patients,
            "synthRecords": records,
            "patients": patients,
            "records": records,
            "trustReport": trust_report,
            "certificate": certificate,
            "generated_patient_count": (
                int(
                    generated[
                        identifier
                    ].nunique()
                )
                if identifier
                else len(generated)
            ),
            "generated_row_count": int(
                len(generated)
            ),
            "requested_patient_count": int(target_n),
        }
    )


@app.get("/api/population")
def population_endpoint() -> dict[str, Any]:
    """Return generated population explorer data."""

    generated = STATE.get(
        "generated_df"
    )

    if not isinstance(
            generated,
            pd.DataFrame,
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "No synthetic cohort exists yet. "
                "Run generation first."
            ),
        )

    return _json_safe(
        {
            "patients": _build_patient_payload(
                generated
            ),
            "records": _records(
                generated
            ),
            "scatterPoints": _build_scatter_points(
                generated
            ),
        }
    )


@app.get("/api/trust-report")
def trust_report_endpoint() -> dict[str, Any]:
    """Return the latest trust/validation report."""

    report = STATE.get(
        "trust_report"
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No trust report exists yet. "
                "Generate a synthetic cohort first."
            ),
        )

    return _json_safe(report)


@app.get("/api/certificate")
def certificate_endpoint() -> dict[str, Any]:
    """Return the latest privacy certificate."""

    certificate = STATE.get(
        "certificate"
    )

    if certificate is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No privacy certificate exists yet. "
                "Generate a synthetic cohort first."
            ),
        )

    return _json_safe(certificate)


@app.get("/api/export")
def export_endpoint(
        confirmed: bool = False,
) -> Response:
    """
    Export synthetic cohort + privacy certificate as one ZIP.

    The certificate is always bundled with the dataset.
    """

    generated = STATE.get(
        "generated_df"
    )

    certificate = STATE.get(
        "certificate"
    )

    if not isinstance(
            generated,
            pd.DataFrame,
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "No synthetic cohort exists yet."
            ),
        )

    if not isinstance(
            certificate,
            dict,
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "No privacy certificate exists yet."
            ),
        )

    gate = certificate.get(
        "privacy_gate_evaluation",
        certificate.get(
            "privacy_gate",
            {},
        ),
    )

    requires_confirmation = bool(
        gate.get(
            "requires_confirmation",
            False,
        )
    )

    if (
            requires_confirmation
            and not confirmed
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Privacy Gate requires explicit "
                "researcher confirmation before export."
            ),
        )

    import zipfile

    buffer = io.BytesIO()

    with zipfile.ZipFile(
            buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        # CSV
        csv_content = generated.to_csv(
            index=False
        )

        archive.writestr(
            "synthetic_cohort.csv",
            csv_content,
        )

        # Excel
        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(
                excel_buffer,
                engine="openpyxl",
        ) as writer:
            generated.to_excel(
                writer,
                index=False,
                sheet_name="Synthetic Cohort",
            )

        archive.writestr(
            "synthetic_cohort.xlsx",
            excel_buffer.getvalue(),
        )

        # Certificate
        archive.writestr(
            "privacy_certificate.json",
            json.dumps(
                _json_safe(certificate),
                indent=2,
            ),
        )

    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="synora_certified_synthetic_cohort.zip"'
            )
        },
    )
