"""
generation.py — Gaussian Copula cross-section + longitudinal synthesis.

Contract:
- generate_cross_sectional(source_df, request: dict, n_rows: int) -> pd.DataFrame
- generate_longitudinal(source_df, synthetic_baseline_df, time_col: str) -> pd.DataFrame
- bootstrap_trajectories(source_df, synthetic_baseline_df, time_col: str) -> pd.DataFrame
"""

from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


LAST_GENERATION_METHOD = {
    "cross_sectional": "gaussian_copula_custom",
    "longitudinal": "trajectory_bootstrapping",
    "notes": [],
}


class GaussianCopulaModel:
    """Gaussian copula synthesizer preserving continuous covariance and empirical marginals."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.columns = []
        self.empirical_marginals = {}
        self.corr_matrix = None

    def fit(self, df: pd.DataFrame):
        self.columns = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        clean_df = df[self.columns].dropna()
        if clean_df.empty:
            clean_df = df[self.columns].fillna(df[self.columns].mean())

        u_data = []
        for col in self.columns:
            vals = clean_df[col].values
            self.empirical_marginals[col] = np.sort(vals)
            ranks = stats.rankdata(vals, method="average") / (len(vals) + 1.0)
            u_data.append(stats.norm.ppf(np.clip(ranks, 1e-6, 1 - 1e-6)))

        z_matrix = np.column_stack(u_data)
        self.corr_matrix = np.corrcoef(z_matrix, rowvar=False)
        if np.ndim(self.corr_matrix) == 0:
            self.corr_matrix = np.array([[1.0]])
        min_eig = np.min(np.real(np.linalg.eigvals(self.corr_matrix)))
        if min_eig < 1e-4:
            self.corr_matrix = self.corr_matrix + (1e-4 - min_eig) * np.eye(self.corr_matrix.shape[0])

    def sample(self, n_samples: int) -> pd.DataFrame:
        rng = np.random.default_rng(self.random_state)
        z_sample = rng.multivariate_normal(
            mean=np.zeros(len(self.columns)),
            cov=self.corr_matrix,
            size=n_samples,
        )
        u_sample = stats.norm.cdf(z_sample)
        synth_dict = {}
        for i, col in enumerate(self.columns):
            empirical = self.empirical_marginals[col]
            indices = (u_sample[:, i] * (len(empirical) - 1)).clip(0, len(empirical) - 1)
            lower = np.floor(indices).astype(int)
            upper = np.ceil(indices).astype(int)
            weight = indices - lower
            synth_dict[col] = (1 - weight) * empirical[lower] + weight * empirical[upper]
        return pd.DataFrame(synth_dict)


def _get_baseline_df(df: pd.DataFrame) -> pd.DataFrame:
    if "patient_id" in df.columns:
        if "month" in df.columns and 1 in df["month"].values:
            base = df[df["month"] == 1].copy()
        else:
            base = df.drop_duplicates(subset=["patient_id"]).copy()
        return base.reset_index(drop=True)
    return df.copy().reset_index(drop=True)


def _try_sdv_gaussian_copula(baseline: pd.DataFrame, n_rows: int) -> Optional[pd.DataFrame]:
    try:
        from sdv.metadata import SingleTableMetadata
        from sdv.single_table import GaussianCopulaSynthesizer
    except Exception:
        return None
    try:
        work = baseline.copy()
        drop_cols = [c for c in ["patient_id", "month"] if c in work.columns]
        work = work.drop(columns=drop_cols)
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(work)
        synth = GaussianCopulaSynthesizer(metadata)
        synth.fit(work)
        return synth.sample(num_rows=n_rows)
    except Exception:
        return None


def generate_cross_sectional(source_df: pd.DataFrame, request: dict, n_rows: int = 1000) -> pd.DataFrame:
    """Gaussian Copula generation conditioned on requested target proportions."""
    global LAST_GENERATION_METHOD
    LAST_GENERATION_METHOD["notes"] = []
    baseline_source = _get_baseline_df(source_df)
    features = [c for c in baseline_source.columns if c not in ["patient_id", "month"]]

    sdv_pool = _try_sdv_gaussian_copula(baseline_source[features], max(n_rows * 4, 4000))
    if sdv_pool is not None:
        pool = sdv_pool
        LAST_GENERATION_METHOD["cross_sectional"] = "sdv_gaussian_copula"
    else:
        copula = GaussianCopulaModel(random_state=42)
        copula.fit(baseline_source[features])
        pool = copula.sample(max(n_rows * 4, 4000))
        LAST_GENERATION_METHOD["cross_sectional"] = "gaussian_copula_custom"
        LAST_GENERATION_METHOD["notes"].append(
            "SDV GaussianCopulaSynthesizer was not available; used an equivalent custom Gaussian copula."
        )

    conditions = request.get("conditions", [])
    if conditions:
        weights = np.ones(len(pool))
        for cond in conditions:
            var = cond.get("variable")
            target_pct = float(cond.get("target_pct", 50.0)) / 100.0
            op = cond.get("operator", "==")
            val = cond.get("value", 1)
            if var not in pool.columns:
                continue
            if op == "==":
                is_match = pool[var].round() == val
            elif op == ">":
                is_match = pool[var] > float(val)
            elif op == "<":
                is_match = pool[var] < float(val)
            elif op == ">=":
                is_match = pool[var] >= float(val)
            elif op == "<=":
                is_match = pool[var] <= float(val)
            else:
                is_match = pool[var] == val
            current_prop = float(is_match.mean())
            if 0.0 < current_prop < 1.0:
                w_pos = target_pct / current_prop
                w_neg = (1 - target_pct) / (1 - current_prop)
                weights *= np.where(is_match, w_pos, w_neg)
        weights = np.clip(weights, 1e-4, 1e4)
        probs = weights / weights.sum()
        rng = np.random.default_rng(42)
        chosen = rng.choice(len(pool), size=n_rows, replace=True, p=probs)
        synth_baseline = pool.iloc[chosen].copy().reset_index(drop=True)
    else:
        synth_baseline = pool.iloc[:n_rows].copy().reset_index(drop=True)

    for col in synth_baseline.columns:
        if col not in source_df.columns:
            continue
        if "diab" in col:
            synth_baseline[col] = (synth_baseline[col] > 0.5).astype(int)
        elif "age" in col:
            synth_baseline[col] = np.clip(synth_baseline[col].round(), 18, 100).astype(int)
        elif "pain" in col:
            synth_baseline[col] = np.clip(synth_baseline[col].round(1), 0.0, 10.0)
        elif "adher" in col:
            synth_baseline[col] = np.clip(synth_baseline[col].round(1), 0.0, 100.0)
        elif "bp" in col:
            synth_baseline[col] = np.clip(synth_baseline[col].round(1), 80.0, 220.0)
        elif "step" in col:
            synth_baseline[col] = np.clip(synth_baseline[col].round(), 0, 25000).astype(int)

    synth_baseline.insert(0, "patient_id", np.arange(1, n_rows + 1))
    return synth_baseline


def bootstrap_trajectories(source_df: pd.DataFrame, synthetic_baseline_df: pd.DataFrame, time_col: str = "month") -> pd.DataFrame:
    """Plan B: resample observed month-to-month deltas from nearest real patients onto synthetic baselines."""
    if time_col not in source_df.columns or "patient_id" not in source_df.columns:
        synth = synthetic_baseline_df.copy()
        synth[time_col] = 1
        return synth

    real_baseline = _get_baseline_df(source_df)
    match_cols = [
        c for c in ["age", "diabetic", "systolic_bp", "activity_steps", "medication_adherence_pct", "pain_score"]
        if c in real_baseline.columns and c in synthetic_baseline_df.columns
    ]
    delta_cols = [c for c in match_cols if c not in ["diabetic", "age"]]

    X_real = real_baseline[match_cols].fillna(real_baseline[match_cols].mean()).values
    X_synth = synthetic_baseline_df[match_cols].fillna(synthetic_baseline_df[match_cols].mean()).values
    scaler = StandardScaler()
    nn = NearestNeighbors(n_neighbors=min(5, len(real_baseline)), metric="euclidean")
    nn.fit(scaler.fit_transform(X_real))
    _, neighbor_indices = nn.kneighbors(scaler.transform(X_synth))

    time_points = sorted(source_df[time_col].unique())
    n_t = len(time_points)
    real_pids = real_baseline["patient_id"].to_numpy()
    pid_to_pos = {int(pid): i for i, pid in enumerate(real_pids)}

    src = source_df.sort_values(["patient_id", time_col])
    delta_lookup = np.zeros((len(real_pids), n_t, len(delta_cols)))
    time_lookup = np.zeros((len(real_pids), n_t))
    for pid, hist in src.groupby("patient_id", sort=False):
        if int(pid) not in pid_to_pos:
            continue
        pos = pid_to_pos[int(pid)]
        hist = hist.set_index(time_col).reindex(time_points)
        vals = hist[delta_cols].ffill().bfill()
        base = vals.iloc[0].to_numpy(dtype=float)
        delta_lookup[pos] = vals.to_numpy(dtype=float) - base
        time_lookup[pos] = np.array(time_points, dtype=float)

    rng = np.random.default_rng(42)
    n_synth = len(synthetic_baseline_df)
    chosen = neighbor_indices[np.arange(n_synth), rng.integers(0, min(3, neighbor_indices.shape[1]), size=n_synth)]

    rows = []
    static_keep = [c for c in synthetic_baseline_df.columns if c not in delta_cols]
    base_static = synthetic_baseline_df[static_keep].to_dict("records")
    base_delta = synthetic_baseline_df[delta_cols].to_numpy(dtype=float)

    for i in range(n_synth):
        deltas = delta_lookup[chosen[i]]
        times = time_lookup[chosen[i]]
        static = base_static[i]
        for t_idx in range(n_t):
            rec = dict(static)
            rec[time_col] = int(times[t_idx])
            for j, c in enumerate(delta_cols):
                val = base_delta[i, j] + deltas[t_idx, j]
                noise = rng.normal(0, max(0.01 * abs(val), 0.1))
                val += noise
                if "pain" in c:
                    val = np.clip(val, 0.0, 10.0)
                elif "adher" in c:
                    val = np.clip(val, 0.0, 100.0)
                elif "bp" in c:
                    val = np.clip(val, 80.0, 220.0)
                elif "step" in c:
                    val = max(0.0, val)
                rec[c] = round(float(val), 1) if ("bp" in c or "pain" in c or "adher" in c) else int(round(val))
            rows.append(rec)

    synth_longitudinal = pd.DataFrame(rows)
    first_cols = ["patient_id", time_col]
    other_cols = [c for c in synth_longitudinal.columns if c not in first_cols]
    return synth_longitudinal[first_cols + other_cols]


def _inject_source_missingness(source_df: pd.DataFrame, generated_df: pd.DataFrame) -> pd.DataFrame:
    """Reproduce source missingness rates so missingness similarity is comparable, not silently complete."""
    out = generated_df.copy()
    rng = np.random.default_rng(7)
    skip = {"patient_id", "month", "age", "diabetic"}
    for col in out.columns:
        if col not in source_df.columns or col in skip:
            continue
        rate = float(source_df[col].isna().mean())
        if rate <= 0:
            continue
        mask = rng.random(len(out)) < rate
        out.loc[mask, col] = np.nan
    return out


def generate_longitudinal(source_df: pd.DataFrame, synthetic_baseline_df: pd.DataFrame, time_col: str = "month") -> pd.DataFrame:
    """Plan A: SDV PARSynthesizer. Plan B: trajectory bootstrapping (used if PAR is unavailable or unstable)."""
    global LAST_GENERATION_METHOD
    par_df = _try_par_synthesizer(source_df, synthetic_baseline_df, time_col)
    if par_df is not None:
        LAST_GENERATION_METHOD["longitudinal"] = "sdv_parsynthesizer"
        return _inject_source_missingness(source_df, par_df)

    LAST_GENERATION_METHOD["longitudinal"] = "trajectory_bootstrapping"
    LAST_GENERATION_METHOD["notes"].append(
        "PARSynthesizer was not available or did not produce stable output; "
        "resampled observed longitudinal change patterns from similar real patients onto synthetic baselines."
    )
    boot = bootstrap_trajectories(source_df, synthetic_baseline_df, time_col=time_col)
    return _inject_source_missingness(source_df, boot)


def _try_par_synthesizer(source_df: pd.DataFrame, synthetic_baseline_df: pd.DataFrame, time_col: str) -> Optional[pd.DataFrame]:
    """Attempt PARSynthesizer only on a small checkpoint. Skip for large n (demo must stay offline-fast)."""
    if time_col not in source_df.columns or "patient_id" not in source_df.columns:
        return None
    if len(synthetic_baseline_df) > 400:
        return None
    try:
        from sdv.metadata import SingleTableMetadata
        from sdv.sequential import PARSynthesizer
    except Exception:
        return None
    try:
        work = source_df.copy()
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(work)
        metadata.set_sequence_key("patient_id")
        metadata.set_sequence_index(time_col)
        model = PARSynthesizer(metadata, epochs=8, verbose=False)
        model.fit(work)
        sampled = model.sample(num_sequences=len(synthetic_baseline_df))
        if sampled is None or sampled.empty or sampled.isna().mean().mean() > 0.5:
            return None
        return sampled
    except Exception:
        return None


def generation_method_summary() -> Dict[str, Any]:
    return dict(LAST_GENERATION_METHOD)
