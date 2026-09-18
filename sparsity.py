"""Source-level sparsity evidence, not a target-achievement mechanism."""
from itertools import combinations
import pandas as pd


def compute_sparsity(df: pd.DataFrame, key_dims: list[str]) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    patient = next((c for c in df if "patient" in c.lower() and "id" in c.lower()), None)
    time = next((c for c in df if c.lower() == "month"), None)
    # Subgroup evidence is patient-level for longitudinal cohorts; rows are
    # retained separately as record_count and never inflate prevalence sixfold.
    cohort = df.sort_values([patient, time]).groupby(patient, as_index=False).first() if patient and time else df
    masks = {}
    for dim in key_dims:
        if dim in cohort:
            masks[dim] = cohort[dim].fillna(0).astype(bool)
        elif dim == "age_over_65" and "age" in cohort:
            masks[dim] = cohort.age > 65
        elif dim == "low_adherence" and "medication_adherence_pct" in cohort:
            masks[dim] = cohort.medication_adherence_pct < 40
        else:
            raise ValueError(f"Unknown sparsity dimension '{dim}'")
    counts = {}
    for size in range(1, min(3, len(key_dims)) + 1):
        for combo in combinations(key_dims, size):
            mask = pd.Series(True, index=cohort.index)
            for dim in combo:
                mask &= masks[dim]
            counts[frozenset(combo)] = int(mask.sum())
    missingness = {c: {"pct": float(df[c].isna().mean() * 100), "bucket": "LOW" if df[c].isna().mean() < .05 else "MODERATE" if df[c].isna().mean() < .2 else "HIGH"} for c in df}
    completeness = float(df.groupby(patient)[time].nunique().mean()) if patient and time else None
    return {"record_count": len(df), "missingness": missingness, "duplicates": {"count": int(df.duplicated().sum()), "bucket": "LOW" if not df.duplicated().any() else "HIGH"}, "subgroup_counts": counts, "rare_subgroups": [(tuple(sorted(k)), v) for k, v in counts.items() if v < 10], "temporal_completeness": completeness}
