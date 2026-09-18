"""
sparsity.py — Source-level dataset sparsity and rare subgroup analysis module.
Contract:
- compute_sparsity(df: pd.DataFrame, key_dims: list[str]) -> dict
"""

import itertools
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np


def compute_sparsity(df: pd.DataFrame, key_dims: List[str] = None) -> Dict[str, Any]:
    """Computes source-level sparsity, missingness buckets, duplicate rate,
    subgroup counts for 1, 2, and 3-way combinations of key dimensions,
    rare subgroup detection (count < 10), and temporal completeness.

    Test against demo_patients.csv: subgroup_counts for
    ('diabetic',) must equal 100, ('diabetic','age_over_65') must equal 25,
    ('diabetic','age_over_65','low_adherence') must equal 2.
    """
    if key_dims is None:
        key_dims = ['diabetic', 'age_over_65', 'low_adherence']

    n_rows = len(df)

    # 1. Missingness analysis
    missingness = {}
    for col in df.columns:
        pct = round(float((df[col].isna().sum() / n_rows) * 100), 2)
        if pct < 5.0:
            bucket = 'LOW'
        elif pct <= 20.0:
            bucket = 'MODERATE'
        else:
            bucket = 'HIGH'
        missingness[col] = {'pct': pct, 'bucket': bucket}

    # 2. Duplicate analysis
    n_dupes = int(df.duplicated().sum())
    dupe_pct = (n_dupes / n_rows) * 100 if n_rows > 0 else 0.0
    if dupe_pct < 1.0:
        dupe_bucket = 'LOW'
    elif dupe_pct <= 5.0:
        dupe_bucket = 'MODERATE'
    else:
        dupe_bucket = 'HIGH'
    duplicates = {'count': n_dupes, 'pct': round(dupe_pct, 2), 'bucket': dupe_bucket}

    # 3. Detect patient structure vs. record level
    has_patient_id = 'patient_id' in df.columns
    has_time = 'month' in df.columns

    # If patient_id is present, analyze patient-level cohort baselines
    if has_patient_id:
        patient_df = df.groupby('patient_id').agg({
            col: 'first' for col in df.columns if col not in ['patient_id', 'month']
        }).reset_index()

        # Specifically for adherence: a patient has low adherence if any observation in their trajectory is < 40
        if 'medication_adherence_pct' in df.columns:
            min_adh = df.groupby('patient_id')['medication_adherence_pct'].min().reset_index()
            patient_df['min_adherence'] = min_adh['medication_adherence_pct']
        else:
            patient_df['min_adherence'] = np.nan

        analysis_df = patient_df
        record_count = int(patient_df['patient_id'].nunique())
    else:
        analysis_df = df.copy()
        record_count = n_rows

    # 4. Dimension evaluation masks on analysis_df
    dim_masks = {}
    for dim in key_dims:
        dim_lower = dim.lower()
        if dim_lower in ['diabetic', 'diabetes']:
            if 'diabetic' in analysis_df.columns:
                dim_masks[dim] = (analysis_df['diabetic'] == 1)
            elif 'diabetes' in analysis_df.columns:
                dim_masks[dim] = (analysis_df['diabetes'] == 1)
            else:
                dim_masks[dim] = pd.Series(False, index=analysis_df.index)

        elif dim_lower in ['age_over_65', 'age>65', 'elderly']:
            if 'age' in analysis_df.columns:
                dim_masks[dim] = (analysis_df['age'] > 65)
            else:
                dim_masks[dim] = pd.Series(False, index=analysis_df.index)

        elif dim_lower in ['low_adherence', 'adherence<40', 'low_adh']:
            if 'min_adherence' in analysis_df.columns and not analysis_df['min_adherence'].isna().all():
                dim_masks[dim] = (analysis_df['min_adherence'] < 40)
            elif 'medication_adherence_pct' in analysis_df.columns:
                dim_masks[dim] = (analysis_df['medication_adherence_pct'] < 40)
            else:
                dim_masks[dim] = pd.Series(False, index=analysis_df.index)
        else:
            # Check if column exists directly
            if dim in analysis_df.columns:
                if pd.api.types.is_numeric_dtype(analysis_df[dim]):
                    dim_masks[dim] = (analysis_df[dim] == 1)
                else:
                    dim_masks[dim] = analysis_df[dim].astype(str).str.lower().isin(['1', 'true', 'yes'])
            else:
                dim_masks[dim] = pd.Series(False, index=analysis_df.index)

    # 5. Enumerate 1, 2, and 3-way combinations
    subgroup_counts = {}
    rare_subgroups = []

    available_dims = list(dim_masks.keys())
    for k in [1, 2, 3]:
        for combo in itertools.combinations(available_dims, k):
            mask = pd.Series(True, index=analysis_df.index)
            for d in combo:
                mask = mask & dim_masks[d]
            count = int(mask.sum())
            subgroup_counts[frozenset(combo)] = count
            if count < 10:
                rare_subgroups.append((combo, count))

    # 6. Temporal completeness calculation
    temporal_completeness = None
    if has_patient_id and has_time:
        max_months = df['month'].nunique()
        counts_per_patient = df.groupby('patient_id')['month'].nunique()
        complete_patients = (counts_per_patient == max_months).sum()
        temporal_completeness = round(float(complete_patients / len(counts_per_patient) * 100), 2)

    return {
        'record_count': record_count,
        'missingness': missingness,
        'duplicates': duplicates,
        'subgroup_counts': subgroup_counts,
        'rare_subgroups': rare_subgroups,
        'temporal_completeness': temporal_completeness
    }
