"""MedSyn Feasibility Engine — Cohort Intelligence (Person 2).

This module serves as the validation firewall before data generation:
"Should we trust this cohort request before generating it?"

It enforces strict separation between:
1. Target Achievement (what the user desires the generator to produce)
2. Source Evidence (what statistical and patient support exists in reality)

It evaluates:
- Cohort request schema validation
- Patient-level individual condition support (1-way)
- Pairwise condition intersections (2-way combinations)
- Triplet condition intersections (3-way combinations)
- Full joint intersection (N-way)
- Evidence categorization: Strong / Moderate / Weak / Sparse
- Sparse-source confirmation gating and clinical risk assessment
"""

from __future__ import annotations

import itertools
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------

class EvidenceTier(str, Enum):
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"
    SPARSE = "Sparse"

    def __str__(self) -> str:
        return self.value

    @property
    def rank(self) -> int:
        """Numeric rank from lowest evidence (0) to highest (3)."""
        ranks = {
            EvidenceTier.SPARSE: 0,
            EvidenceTier.WEAK: 1,
            EvidenceTier.MODERATE: 2,
            EvidenceTier.STRONG: 3,
        }
        return ranks[self]


SUPPORTED_OPERATORS = {
    "==", "!=", ">", ">=", "<", "<=", "in", "not in"
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CohortRequestError(ValueError):
    """Raised when a cohort request specification is invalid."""


class CohortValidationError(CohortRequestError):
    """Raised when a cohort request fails schema or dataset validation."""


# ---------------------------------------------------------------------------
# Schema Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CohortCondition:
    """Specification of a single cohort filtering or conditioning rule."""
    variable: str
    operator: str
    value: Any
    target_pct: float
    label: Optional[str] = None

    def __post_init__(self) -> None:
        self.variable = str(self.variable).strip()
        self.operator = str(self.operator).strip()
        if self.operator not in SUPPORTED_OPERATORS:
            raise CohortValidationError(
                f"Unsupported operator '{self.operator}'. Supported: {sorted(SUPPORTED_OPERATORS)}"
            )
        try:
            self.target_pct = float(self.target_pct)
        except (TypeError, ValueError) as exc:
            raise CohortValidationError(
                f"target_pct must be numeric, got {self.target_pct!r}"
            ) from exc

        if not (0.0 <= self.target_pct <= 100.0):
            raise CohortValidationError(
                f"target_pct must be between 0.0 and 100.0, got {self.target_pct}"
            )

    def format_expression(self) -> str:
        """Return human-readable representation of the condition."""
        if self.label:
            return f"{self.label} ({self.variable} {self.operator} {self.value})"
        return f"{self.variable} {self.operator} {self.value}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable,
            "operator": self.operator,
            "value": self.value,
            "target_pct": self.target_pct,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CohortCondition":
        if not isinstance(data, Mapping):
            raise CohortValidationError("Condition must be a mapping/dict")
        for req_field in ("variable", "operator", "value", "target_pct"):
            if req_field not in data:
                raise CohortValidationError(f"Missing required condition field: '{req_field}'")
        return cls(
            variable=str(data["variable"]),
            operator=str(data["operator"]),
            value=data["value"],
            target_pct=float(data["target_pct"]),
            label=data.get("label"),
        )


@dataclass
class CohortRequest:
    """Complete specification of a synthetic cohort generation request."""
    target_n: int
    conditions: List[CohortCondition] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        try:
            self.target_n = int(self.target_n)
        except (TypeError, ValueError) as exc:
            raise CohortValidationError(f"target_n must be an integer, got {self.target_n!r}") from exc

        if self.target_n <= 0:
            raise CohortValidationError(f"target_n must be > 0, got {self.target_n}")

        parsed_conditions: List[CohortCondition] = []
        for idx, cond in enumerate(self.conditions):
            if isinstance(cond, CohortCondition):
                parsed_conditions.append(cond)
            elif isinstance(cond, Mapping):
                parsed_conditions.append(CohortCondition.from_dict(cond))
            else:
                raise CohortValidationError(
                    f"Condition at index {idx} must be CohortCondition or dict, got {type(cond).__name__}"
                )
        self.conditions = parsed_conditions

    def validate_against_dataset(self, data: pd.DataFrame) -> None:
        """Validate that all referenced variables exist and have compatible types."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        if data.empty:
            raise ValueError("Source dataset is empty")

        missing = [c.variable for c in self.conditions if c.variable not in data.columns]
        if missing:
            raise CohortValidationError(
                f"Conditions reference variables not present in dataset: {missing}. "
                f"Available columns: {list(data.columns)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_n": self.target_n,
            "conditions": [c.to_dict() for c in self.conditions],
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CohortRequest":
        if not isinstance(data, Mapping):
            raise CohortValidationError("CohortRequest data must be a mapping/dict")
        target_n = data.get("target_n", 1000)
        conditions = data.get("conditions", [])
        return cls(
            target_n=int(target_n),
            conditions=conditions,
            metadata=data.get("metadata"),
        )


# ---------------------------------------------------------------------------
# Patient Identifier & Mask Utilities
# ---------------------------------------------------------------------------

def find_patient_identifier(data: pd.DataFrame) -> Optional[str]:
    """Find a candidate patient identifier column in the dataset."""
    for col in data.columns:
        col_lower = str(col).lower().replace(" ", "_")
        if any(token in col_lower for token in ("patient_id", "subject_id", "participant_id", "mrn", "patientid")):
            return col
    for col in data.columns:
        col_lower = str(col).lower()
        if ("patient" in col_lower or "subject" in col_lower) and "id" in col_lower:
            return col
    for col in data.columns:
        if str(col).lower() in {"id", "uuid", "patient"}:
            return col
    return None


def evaluate_condition_mask(data: pd.DataFrame, condition: CohortCondition) -> pd.Series:
    """Evaluate a boolean mask for a single condition over the DataFrame."""
    var = condition.variable
    if var not in data.columns:
        return pd.Series(False, index=data.index)

    series = data[var]
    op = condition.operator
    val = condition.value

    # Type coercion if series is numeric
    if pd.api.types.is_numeric_dtype(series):
        try:
            if not isinstance(val, (list, tuple, set)):
                val = float(val) if "." in str(val) else int(val)
        except (ValueError, TypeError):
            pass

    if op == "==":
        return series == val
    elif op == "!=":
        return series != val
    elif op == ">":
        return series > val
    elif op == ">=":
        return series >= val
    elif op == "<":
        return series < val
    elif op == "<=":
        return series <= val
    elif op == "in":
        val_set = val if isinstance(val, (list, tuple, set)) else [val]
        return series.isin(val_set)
    elif op == "not in":
        val_set = val if isinstance(val, (list, tuple, set)) else [val]
        return ~series.isin(val_set)
    else:
        return pd.Series(False, index=data.index)


# ---------------------------------------------------------------------------
# Evidence Tier Classification
# ---------------------------------------------------------------------------

def classify_evidence(count: int, pct: float, total_patients: int) -> EvidenceTier:
    """Classify evidence strength into Strong, Moderate, Weak, or Sparse.

    Thresholds:
    - Sparse (⚠️): count < 10 OR pct < 1.0% (severe memorization/collapse risk)
    - Weak (⚠️): count < 30 OR (pct < 5.0% and count < 50)
    - Moderate (ℹ️): count < 100 OR pct < 20.0%
    - Strong (✅): count >= 100 AND pct >= 20.0% (or count >= 150)
    """
    if count < 10 or pct < 1.0 or count == 0:
        return EvidenceTier.SPARSE
    elif count < 30 or (pct < 5.0 and count < 50):
        return EvidenceTier.WEAK
    elif count < 100 or pct < 20.0:
        return EvidenceTier.MODERATE
    else:
        return EvidenceTier.STRONG


# ---------------------------------------------------------------------------
# Feasibility Evaluation Report Object
# ---------------------------------------------------------------------------

class FeasibilityResult(Mapping):
    """Dictionary-compatible container for feasibility evaluation results.

    Implements the Mapping interface so `result['overall']`, `result.get('conditions')`,
    etc., work identically to a standard dict, ensuring seamless Streamlit integration.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterable[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @property
    def overall(self) -> str:
        return str(self._data.get("overall", "Sparse"))

    @property
    def status(self) -> str:
        return self.overall

    @property
    def is_sparse(self) -> bool:
        return self.overall.lower() == "sparse"

    @property
    def requires_confirmation(self) -> bool:
        return bool(self._data.get("requires_confirmation", self.is_sparse))

    @property
    def conditions(self) -> List[Dict[str, Any]]:
        return list(self._data.get("conditions", []))

    @property
    def combination(self) -> Dict[str, Any]:
        return dict(self._data.get("combination", {}))

    @property
    def two_way_combinations(self) -> List[Dict[str, Any]]:
        return list(self._data.get("two_way_combinations", []))

    @property
    def three_way_combinations(self) -> List[Dict[str, Any]]:
        return list(self._data.get("three_way_combinations", []))

    def to_dataframe(self) -> pd.DataFrame:
        """Return the conditions evidence as a displayable pandas DataFrame."""
        return pd.DataFrame(self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        """Return clean serializable dictionary."""
        return dict(self._data)

    def summary(self) -> str:
        """Human-readable markdown summary of the feasibility evaluation."""
        lines = [
            f"### Feasibility Evaluation: {self.overall.upper()}",
            f"- **Overall Evidence Status**: {self.overall}",
            f"- **Requires Confirmation**: {'YES ⚠️' if self.requires_confirmation else 'No'}",
        ]
        if self.requires_confirmation:
            lines.append(f"> ⚠️ **Warning**: {self.get('confirmation_message', '')}")
        lines.append("\n**Individual Conditions:**")
        for cond in self.conditions:
            lines.append(
                f"- `{cond['Variable']} {cond['Operator']} {cond['Threshold']}`: "
                f"Source {cond['Source count']} ({cond['Source %']}%) → Target {cond['Target %']}% "
                f"[{cond['Evidence']}]"
            )
        combo = self.combination
        if combo:
            lines.append(
                f"\n**{combo.get('label', 'Joint Combination')} (Order {combo.get('order', 1)}):** "
                f"{combo.get('source_count')} patients ({combo.get('source_pct')}%) → [{combo.get('Evidence')}]"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core Feasibility Engine
# ---------------------------------------------------------------------------

def check_feasibility(
    data: pd.DataFrame,
    request: Union[CohortRequest, Mapping[str, Any]],
) -> FeasibilityResult:
    """Evaluate whether a cohort request is feasible based on source evidence.

    Answering the foundational question:
    "Should we trust this request before generating it?"

    Args:
        data: Source pandas DataFrame (real clinical observations).
        request: CohortRequest object or mapping with 'target_n' and 'conditions'.

    Returns:
        FeasibilityResult containing overall evidence tier, individual condition
        evidence, 2-way combinations, 3-way combinations, N-way intersection,
        and sparse confirmation requirements.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"data must be a pandas DataFrame, got {type(data).__name__}")
    if data.empty:
        raise ValueError("Cannot evaluate feasibility on an empty dataset")

    # Normalize request into CohortRequest dataclass
    if isinstance(request, CohortRequest):
        cohort_req = request
    elif isinstance(request, Mapping):
        cohort_req = CohortRequest.from_dict(request)
    else:
        raise TypeError("request must be CohortRequest or Mapping")

    cohort_req.validate_against_dataset(data)

    patient_col = find_patient_identifier(data)
    total_patients = data[patient_col].nunique() if patient_col else len(data)

    def count_distinct_patients(mask: pd.Series) -> int:
        if patient_col:
            return int(data.loc[mask, patient_col].nunique())
        return int(mask.sum())

    conditions = cohort_req.conditions
    n_cond = len(conditions)

    # -----------------------------------------------------------------------
    # 1. Individual Condition Checking (1-Way)
    # -----------------------------------------------------------------------
    individual_rows: List[Dict[str, Any]] = []
    masks: List[pd.Series] = []
    condition_tiers: List[EvidenceTier] = []

    for cond in conditions:
        mask = evaluate_condition_mask(data, cond)
        masks.append(mask)

        count = count_distinct_patients(mask)
        pct = round(count / max(total_patients, 1) * 100, 2)
        tier = classify_evidence(count, pct, total_patients)
        condition_tiers.append(tier)

        shift = round(cond.target_pct - pct, 2)
        shift_str = f"+{shift}%" if shift > 0 else f"{shift}%"

        # Risk description for this condition
        if abs(shift) > 30:
            risk = "Severe Shift (High Divergence)"
        elif abs(shift) > 15:
            risk = "Moderate Shift"
        else:
            risk = "Aligned with Source"

        individual_rows.append({
            "Variable": cond.variable,
            "Operator": cond.operator,
            "Threshold": cond.value,
            "Condition": cond.format_expression(),
            "Target %": cond.target_pct,
            "Source count": count,
            "Source %": pct,
            "Shift (Δ)": shift_str,
            "Evidence": str(tier),
            "Risk": risk,
            # Lowercase keys for programmatic access
            "variable": cond.variable,
            "operator": cond.operator,
            "value": cond.value,
            "target_pct": cond.target_pct,
            "source_count": count,
            "source_pct": pct,
            "evidence": str(tier),
        })

    # -----------------------------------------------------------------------
    # 2. Pairwise Condition Combinations (2-Way)
    # -----------------------------------------------------------------------
    two_way_rows: List[Dict[str, Any]] = []
    two_way_tiers: List[EvidenceTier] = []

    if n_cond >= 2:
        for (i, cond_i), (j, cond_j) in itertools.combinations(enumerate(conditions), 2):
            joint_mask = masks[i] & masks[j]
            joint_count = count_distinct_patients(joint_mask)
            joint_pct = round(joint_count / max(total_patients, 1) * 100, 2)
            tier = classify_evidence(joint_count, joint_pct, total_patients)
            two_way_tiers.append(tier)

            # Expected percentage under independence assumption
            p_i = individual_rows[i]["Source %"]
            p_j = individual_rows[j]["Source %"]
            expected_pct = round((p_i * p_j) / 100.0, 2)
            obs_exp_ratio = round(joint_pct / max(expected_pct, 0.01), 2)

            two_way_rows.append({
                "Combination": f"{cond_i.variable} & {cond_j.variable}",
                "Variables": [cond_i.variable, cond_j.variable],
                "Source count": joint_count,
                "Source %": joint_pct,
                "Expected independent %": expected_pct,
                "Obs/Exp ratio": obs_exp_ratio,
                "Evidence": str(tier),
                # Lowercase keys
                "source_count": joint_count,
                "source_pct": joint_pct,
                "evidence": str(tier),
            })

    # -----------------------------------------------------------------------
    # 3. Triplet Condition Combinations (3-Way)
    # -----------------------------------------------------------------------
    three_way_rows: List[Dict[str, Any]] = []
    three_way_tiers: List[EvidenceTier] = []

    if n_cond >= 3:
        for (i, c_i), (j, c_j), (k, c_k) in itertools.combinations(enumerate(conditions), 3):
            joint_mask = masks[i] & masks[j] & masks[k]
            joint_count = count_distinct_patients(joint_mask)
            joint_pct = round(joint_count / max(total_patients, 1) * 100, 2)
            tier = classify_evidence(joint_count, joint_pct, total_patients)
            three_way_tiers.append(tier)

            three_way_rows.append({
                "Combination": f"{c_i.variable} & {c_j.variable} & {c_k.variable}",
                "Variables": [c_i.variable, c_j.variable, c_k.variable],
                "Source count": joint_count,
                "Source %": joint_pct,
                "Evidence": str(tier),
                # Lowercase keys
                "source_count": joint_count,
                "source_pct": joint_pct,
                "evidence": str(tier),
            })

    # -----------------------------------------------------------------------
    # 4. N-Way / Full Joint Combination
    # -----------------------------------------------------------------------
    if masks:
        full_mask = np.logical_and.reduce(masks)
        full_count = count_distinct_patients(full_mask)
        full_pct = round(full_count / max(total_patients, 1) * 100, 2)
    else:
        full_count = total_patients
        full_pct = 100.0

    full_tier = classify_evidence(full_count, full_pct, total_patients)

    combo_label = (
        "Single condition" if n_cond == 1
        else "2-way combo" if n_cond == 2
        else "Triple combo" if n_cond == 3
        else f"{n_cond}-way combination"
    )

    combination_dict = {
        "order": n_cond,
        "label": combo_label,
        "source_count": full_count,
        "source_pct": full_pct,
        "evidence": str(full_tier),
        "Evidence": str(full_tier),
    }

    # -----------------------------------------------------------------------
    # 5. Overall Feasibility & Confirmation Gate
    # -----------------------------------------------------------------------
    # The overall rating is governed by the weakest link:
    # If the joint intersection is Sparse, the overall status is Sparse.
    all_evaluated_tiers = condition_tiers + two_way_tiers + three_way_tiers + [full_tier]
    if not all_evaluated_tiers:
        overall_tier = EvidenceTier.STRONG
    else:
        # Minimum rank dictates the weakest link
        min_tier = min(all_evaluated_tiers, key=lambda t: t.rank)
        # Joint intersection has high veto power
        if full_tier == EvidenceTier.SPARSE:
            overall_tier = EvidenceTier.SPARSE
        else:
            overall_tier = min_tier

    overall_str = str(overall_tier)
    requires_confirmation = (overall_tier == EvidenceTier.SPARSE)

    # Detailed confirmation message when sparse
    if requires_confirmation:
        target_patients_matching = int(cohort_req.target_n * (max(c.target_pct for c in conditions) / 100.0)) if conditions else 0
        confirmation_message = (
            f"Sparse source evidence detected: Only {full_count} patient(s) ({full_pct}%) "
            f"in the source dataset ({total_patients} total patients) satisfy the requested combination. "
            f"Forcing the generative model to produce this subgroup will cause extreme oversampling, "
            f"severe identity memorization (1-NN distance = 0), and membership inference privacy leakage. "
            f"Explicit confirmation is required to proceed with generation."
        )
    elif overall_tier == EvidenceTier.WEAK:
        confirmation_message = (
            f"Weak source evidence detected ({full_count} patients, {full_pct}%). "
            f"Statistical parameter estimation in generative models will have high variance for this subgroup."
        )
    else:
        confirmation_message = "Source evidence is sufficient for reliable cohort generation."

    # Actionable recommendations
    recommendations: List[str] = []
    if requires_confirmation:
        recommendations.append("Relax condition thresholds (e.g. broaden age bands or adherence ranges).")
        recommendations.append("Lower target percentages closer to observed source prevalence.")
        recommendations.append("Collect additional real patient records to support this clinical subgroup.")
        recommendations.append("If generating anyway, strictly review the Privacy Audit and Nearest-Neighbor report.")
    elif overall_tier == EvidenceTier.WEAK:
        recommendations.append("Compare Gaussian Copula vs CTGAN results carefully in the Sanity Checks.")
        recommendations.append("Inspect correlation heatmaps to verify no spurious associations were synthesized.")
    else:
        recommendations.append("Source evidence is strong. Proceed to Generation Engine.")

    result_payload: Dict[str, Any] = {
        "overall": overall_str,
        "status": overall_str,
        "feasibility": overall_str,
        "total_source_patients": total_patients,
        "patient_identifier_used": patient_col or "Row counts (no patient ID detected)",
        "conditions": individual_rows,
        "combination": combination_dict,
        "two_way_combinations": two_way_rows,
        "three_way_combinations": three_way_rows,
        "requires_confirmation": requires_confirmation,
        "confirmation_message": confirmation_message,
        "recommendations": recommendations,
        "development_fallback": False,
    }

    return FeasibilityResult(result_payload)


# Aliases for flexible import matching
evaluate_feasibility = check_feasibility
assess_feasibility = check_feasibility


def validate_cohort_request(
    request: Union[CohortRequest, Mapping[str, Any]],
    data: Optional[pd.DataFrame] = None,
) -> CohortRequest:
    """Validate and normalize a cohort request structure."""
    if isinstance(request, CohortRequest):
        req = request
    elif isinstance(request, Mapping):
        req = CohortRequest.from_dict(request)
    else:
        raise CohortValidationError(f"Expected CohortRequest or mapping, got {type(request).__name__}")

    if data is not None:
        req.validate_against_dataset(data)

    return req


def confirm_sparse(
    request: Union[CohortRequest, Mapping[str, Any]],
    acknowledged: bool = False,
) -> bool:
    """Validate that the user has explicitly confirmed proceeding with a sparse request."""
    if not acknowledged:
        raise PermissionError(
            "Generation on sparse source evidence requires explicit confirmation (acknowledged=True)."
        )
    return True
