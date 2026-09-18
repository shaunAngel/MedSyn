"""
feasibility.py - Evidence-aware cohort feasibility engine.

The gate evaluates requested conjunctions against patient-level source evidence.
It reports support tiers separately from target achievement so generation never
silently turns a requested percentage into an evidence claim.
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd


TIER_ORDER = {"Sparse": 0, "Weak": 1, "Moderate": 2, "Strong": 3}


def classify_support(count: int) -> str:
    """Classify an observed patient count using Cohortly's evidence thresholds."""
    count = int(count)
    if count >= 30:
        return "Strong"
    if count >= 10:
        return "Moderate"
    if count >= 3:
        return "Weak"
    return "Sparse"


def _patient_frame(sparsity_output: Dict[str, Any]) -> int:
    return int(sparsity_output.get("record_count", 0))


def _dimension_alias(variable: str) -> str:
    normalized = variable.strip().lower()
    if normalized in {"diabetic", "diabetes"}:
        return "diabetic"
    if normalized in {"age_over_65", "age>65", "elderly", "age"}:
        return "age_over_65"
    if normalized in {"low_adherence", "adherence<40", "low_adh", "medication_adherence_pct"}:
        return "low_adherence"
    return normalized


def _condition_dimension(condition: Dict[str, Any]) -> str:
    return _dimension_alias(str(condition.get("variable", "")))


def _condition_label(condition: Dict[str, Any]) -> str:
    variable = str(condition.get("variable", "condition"))
    operator = str(condition.get("operator", "=="))
    value = condition.get("value", 1)
    if variable == "diabetic" and operator == "==" and value == 1:
        return "Diabetic"
    if variable == "age" and operator == ">" and float(value) == 65:
        return "Age > 65"
    if variable == "medication_adherence_pct" and operator == "<" and float(value) == 40:
        return "Low adherence < 40%"
    return f"{variable} {operator} {value}"


def _requested_dimensions(request: Dict[str, Any]) -> List[str]:
    dimensions = []
    for condition in request.get("conditions", []):
        dimension = _condition_dimension(condition)
        if dimension and dimension not in dimensions:
            dimensions.append(dimension)
    return dimensions


def _lookup_count(sparsity_output: Dict[str, Any], dimensions: Iterable[str]) -> int:
    subgroup_counts = sparsity_output.get("subgroup_counts", {})
    return int(subgroup_counts.get(frozenset(dimensions), 0))


def evaluate_cohort_request(request: Dict[str, Any], sparsity_output: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate individual conditions and their full conjunction against evidence."""
    if not sparsity_output:
        return {
            "overall_tier": "Sparse",
            "requires_confirmation": True,
            "per_combination": [],
            "source_count": 0,
            "source_pct": 0.0,
            "target_n": int(request.get("target_n", 0)),
            "warning": "No source evidence is available for this request.",
        }

    record_count = _patient_frame(sparsity_output)
    conditions = request.get("conditions", [])
    dimensions = _requested_dimensions(request)
    combinations: List[Tuple[str, ...]] = []

    # Report each requested marginal and then the complete conjunction.
    for size in range(1, len(dimensions) + 1):
        combinations.extend(itertools.combinations(dimensions, size))

    per_combination: List[Dict[str, Any]] = []
    for combination in combinations:
        source_count = _lookup_count(sparsity_output, combination)
        source_pct = round((source_count / record_count * 100.0), 2) if record_count else 0.0
        matching_conditions = [
            condition for condition in conditions
            if _condition_dimension(condition) in combination
        ]
        target_pct = round(
            min((float(condition.get("target_pct", 0.0)) for condition in matching_conditions), default=0.0),
            2,
        )
        per_combination.append({
            "dimensions": list(combination),
            "condition_labels": [
                _condition_label(condition)
                for condition in matching_conditions
            ],
            "source_count": source_count,
            "source_pct": source_pct,
            "target_pct": target_pct,
            "tier": classify_support(source_count),
        })

    full_count = _lookup_count(sparsity_output, dimensions)
    full_pct = round((full_count / record_count * 100.0), 2) if record_count else 0.0
    overall_tier = classify_support(full_count)
    target_n = int(request.get("target_n", 0))
    target_pct = round(
        min((float(condition.get("target_pct", 0.0)) for condition in conditions), default=0.0),
        2,
    )
    warning = (
        f"SPARSE EVIDENCE: Only {full_count} source records satisfy all requested conditions. "
        f"Requested {target_n:,}. Extrapolation required."
        if overall_tier == "Sparse"
        else None
    )

    return {
        "overall_tier": overall_tier,
        "requires_confirmation": overall_tier in {"Sparse", "Weak"},
        "per_combination": per_combination,
        "source_count": full_count,
        "source_pct": full_pct,
        "target_pct": target_pct,
        "target_n": target_n,
        "warning": warning,
    }
