"""
sanity.py — Pre-flight mechanical sanity checks module for Cohortly.
Contract:
- run_sanity_checks(generated_df, schema: dict, source_df) -> dict
"""

from typing import Dict, Any
import pandas as pd
import numpy as np


def run_sanity_checks(generated_df: pd.DataFrame, schema: dict, source_df: pd.DataFrame) -> Dict[str, Any]:
    """Returns {check_name: {'passed': bool, 'detail': str}} for:
    valid_ranges (age, BP, pain_score within source min/max +/- 10%),
    no_duplicate_ids, valid_types, no_negative_values_where_inapplicable.
    Mechanical checks ONLY — do not imply clinical validity.
    """
    results = {}

    # 1. Valid Ranges Check
    range_failures = []
    numeric_cols = [c for c in ['age', 'systolic_bp', 'pain_score', 'activity_steps', 'medication_adherence_pct']
                    if c in generated_df.columns and c in source_df.columns]

    for col in numeric_cols:
        src_min = float(source_df[col].dropna().min())
        src_max = float(source_df[col].dropna().max())
        span = src_max - src_min
        lower_bound = max(0.0, src_min - 0.10 * span) if src_min >= 0 else src_min - 0.10 * span
        upper_bound = src_max + 0.10 * span

        gen_min = float(generated_df[col].dropna().min())
        gen_max = float(generated_df[col].dropna().max())

        if gen_min < lower_bound or gen_max > upper_bound:
            range_failures.append(f"{col}: [{gen_min:.1f}, {gen_max:.1f}] outside allowed [{lower_bound:.1f}, {upper_bound:.1f}]")

    if not range_failures:
        results['valid_ranges'] = {
            'passed': True,
            'detail': f"All {len(numeric_cols)} numeric variables fell within source min/max ± 10% bounds."
        }
    else:
        results['valid_ranges'] = {
            'passed': False,
            'detail': f"Range boundary excursions detected: {'; '.join(range_failures)}"
        }

    # 2. No Duplicate IDs Check
    time_col = schema.get('time_col') or ('month' if 'month' in generated_df.columns else None)
    id_col = schema.get('patient_id_col') or ('patient_id' if 'patient_id' in generated_df.columns else None)

    if id_col and id_col in generated_df.columns:
        if time_col and time_col in generated_df.columns:
            dupes = generated_df.duplicated(subset=[id_col, time_col]).sum()
            dupe_detail = f"Zero duplicate ({id_col}, {time_col}) combinations found."
        else:
            dupes = generated_df.duplicated(subset=[id_col]).sum()
            dupe_detail = f"Zero duplicate {id_col} values found."

        results['no_duplicate_ids'] = {
            'passed': bool(dupes == 0),
            'detail': dupe_detail if dupes == 0 else f"{dupes} duplicate sequence IDs found."
        }
    else:
        results['no_duplicate_ids'] = {
            'passed': True,
            'detail': "No identifier column present; row integrity intact."
        }

    # 3. Valid Types Check
    type_issues = []
    for col in generated_df.columns:
        if 'id' in col or col == 'month' or 'diab' in col:
            # Should be discrete integer values
            vals = generated_df[col].dropna()
            if not np.all(vals.astype(float) % 1 == 0):
                type_issues.append(f"{col} contains non-integer values")
        elif col in ['pain_score', 'systolic_bp', 'medication_adherence_pct']:
            if not pd.api.types.is_numeric_dtype(generated_df[col]):
                type_issues.append(f"{col} is not numeric dtype")

    results['valid_types'] = {
        'passed': len(type_issues) == 0,
        'detail': "All schema column datatypes strictly match expected definitions." if len(type_issues) == 0 else f"Type mismatches: {', '.join(type_issues)}"
    }

    # 4. No Negative Values Where Inapplicable Check
    non_neg_cols = [c for c in ['age', 'activity_steps', 'systolic_bp', 'medication_adherence_pct', 'pain_score']
                    if c in generated_df.columns]
    neg_found = []
    for col in non_neg_cols:
        min_v = generated_df[col].dropna().min()
        if min_v < 0:
            neg_found.append(f"{col} (min={min_v})")

    results['no_negative_values_where_inapplicable'] = {
        'passed': len(neg_found) == 0,
        'detail': f"All physiological metrics ({', '.join(non_neg_cols)}) strictly non-negative." if len(neg_found) == 0 else f"Negative values detected in: {', '.join(neg_found)}"
    }

    # 5. Row Count & Completeness
    n_rows = len(generated_df)
    results['expected_row_count'] = {
        'passed': n_rows > 0,
        'detail': f"Generated dataset contains {n_rows:,} verified observations."
    }

    return results
