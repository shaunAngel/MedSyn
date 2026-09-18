"""
test_cohortly.py — Automated acceptance test suite for Cohortly modules.
"""

import sys
import pandas as pd
import numpy as np

from data_ingest import load_dataset, detect_schema
from sparsity import compute_sparsity
from feasibility import evaluate_cohort_request, classify_support
from shift import compute_population_shift, target_achievement
from generation import generate_cross_sectional, generate_longitudinal
from sanity import run_sanity_checks
from validation import (
    compute_quality_metrics,
    compute_privacy_metrics,
    compute_missingness_similarity,
    compute_tstr
)


def run_all_tests():
    print("========================================")
    print("COHORTLY AUTOMATED ACCEPTANCE TEST SUITE")
    print("========================================")

    # 1. Test Ingest & Schema
    print("\n[TEST 1] Testing data_ingest.py...")
    df = load_dataset("demo_patients.csv")
    assert df.shape == (3000, 8), f"Unexpected shape {df.shape}"
    schema = detect_schema(df)
    assert schema['patient_id_col'] == 'patient_id'
    assert schema['time_col'] == 'month'
    assert 'diabetic' in schema['binary_cols']
    assert 'systolic_bp' in schema['numeric_cols']
    print("[OK] data_ingest.py passed!")

    # 2. Test Sparsity
    print("\n[TEST 2] Testing sparsity.py against specification benchmarks...")
    sp = compute_sparsity(df, ['diabetic', 'age_over_65', 'low_adherence'])
    cnt_diab = sp['subgroup_counts'][frozenset(['diabetic'])]
    cnt_diab_age = sp['subgroup_counts'][frozenset(['diabetic', 'age_over_65'])]
    cnt_triple = sp['subgroup_counts'][frozenset(['diabetic', 'age_over_65', 'low_adherence'])]

    print(f"  Diabetic count: {cnt_diab} (Expected: 100)")
    print(f"  Diabetic + Age>65 count: {cnt_diab_age} (Expected: 25)")
    print(f"  Diabetic + Age>65 + Low adherence: {cnt_triple} (Expected: 2)")

    assert cnt_diab == 100, f"Expected 100 diabetic, got {cnt_diab}"
    assert cnt_diab_age == 25, f"Expected 25 diabetic+age>65, got {cnt_diab_age}"
    assert cnt_triple == 2, f"Expected 2 triple combination, got {cnt_triple}"
    assert sp['record_count'] == 500, f"Expected 500 patients, got {sp['record_count']}"
    assert sp['temporal_completeness'] == 100.0
    print("[OK] sparsity.py passed all benchmark checks!")

    # 3. Test Feasibility
    print("\n[TEST 3] Testing feasibility.py gate...")
    req_sparse = {
        'target_n': 10000,
        'conditions': [
            {'variable': 'diabetic', 'operator': '==', 'value': 1, 'target_pct': 60},
            {'variable': 'age', 'operator': '>', 'value': 65, 'target_pct': 50},
            {'variable': 'medication_adherence_pct', 'operator': '<', 'value': 40, 'target_pct': 40}
        ]
    }
    feas_sparse = evaluate_cohort_request(req_sparse, sp)
    assert feas_sparse['overall_tier'] == 'Sparse', f"Expected Sparse, got {feas_sparse['overall_tier']}"
    assert feas_sparse['requires_confirmation'] is True

    req_strong = {
        'target_n': 1000,
        'conditions': [
            {'variable': 'diabetic', 'operator': '==', 'value': 1, 'target_pct': 30}
        ]
    }
    feas_strong = evaluate_cohort_request(req_strong, sp)
    assert feas_strong['overall_tier'] == 'Strong', f"Expected Strong, got {feas_strong['overall_tier']}"
    assert feas_strong['requires_confirmation'] is False
    print("[OK] feasibility.py passed all gate evaluations!")

    # 4. Test Generation & Trajectory Bootstrapping
    print("\n[TEST 4] Testing generation.py (Copula + Trajectory Bootstrapping)...")
    synth_base = generate_cross_sectional(df, req_sparse, n_rows=200)
    assert len(synth_base) == 200
    assert 'patient_id' in synth_base.columns

    synth_long = generate_longitudinal(df, synth_base, time_col='month')
    assert len(synth_long) == 200 * 6, f"Expected 1,200 longitudinal records, got {len(synth_long)}"
    print(f"  Generated {len(synth_long):,} records across 200 synthetic trajectories.")
    print("[OK] generation.py passed!")

    # 5. Test Pre-flight Sanity Checks
    print("\n[TEST 5] Testing sanity.py...")
    sanity = run_sanity_checks(synth_long, schema, df)
    assert sanity['valid_ranges']['passed'] is True
    assert sanity['no_duplicate_ids']['passed'] is True
    assert sanity['valid_types']['passed'] is True
    assert sanity['no_negative_values_where_inapplicable']['passed'] is True
    print("[OK] sanity.py passed all pre-flight checks!")

    # 6. Test Population Shift
    print("\n[TEST 6] Testing shift.py...")
    shift_df = compute_population_shift(df, req_sparse, synth_long)
    assert list(shift_df.columns) == ['variable', 'source_pct', 'target_pct', 'generated_pct']
    print("  Population Shift table computed:")
    for _, row in shift_df.iterrows():
        print(f"    {row['variable']}: Source={row['source_pct']}%, Target={row['target_pct']}%, Generated={row['generated_pct']}%")
    print("[OK] shift.py passed!")

    # 7. Test Validation Suite
    print("\n[TEST 7] Testing validation.py (Quality, Privacy DCR, TSTR Utility)...")
    q = compute_quality_metrics(df, synth_long)
    assert q['overall_quality_score'] > 80.0
    print(f"  Quality Score: {q['overall_quality_score']}%")

    p = compute_privacy_metrics(df, synth_long)
    assert p['metric_name'] == 'distance_to_closest_record'
    assert p['value'] > 0.0
    print(f"  Privacy DCR: {p['value']:.3f} (Label: {p['label']})")

    t = compute_tstr(df, synth_long)
    if t['available']:
        print(f"  TSTR Retention: {t['utility_retention_pct']}%")

    print("[OK] validation.py passed!")
    print("\n========================================")
    print("ALL 7 MODULE ACCEPTANCE TESTS PASSED 100%")
    print("========================================")


if __name__ == "__main__":
    run_all_tests()
