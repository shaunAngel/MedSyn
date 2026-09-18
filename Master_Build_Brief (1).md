# Synthetic Patient Cohort Platform — Master Build Brief
**For: Antigravity agent-assisted build (Manager view, 4 parallel agents + 1 human integrator)**
**Everything an agent needs to build its module without guessing is in this document.**

---

## 1. Product thesis

> SDV/SDMetrics already generate and evaluate synthetic tabular data. **Our product is the decision layer**: before generation, it tells a researcher whether their requested cohort is actually supported by evidence in their source data; after generation, it explains what was preserved, what was intentionally changed, and where the system had to extrapolate — in language a clinical researcher can act on.

**Positioning:** Synthetic patient cohorts for research teams who don't have millions of records — generated, checked, and proven trustworthy before you download a single row.

**Never claim:** clinical accuracy, medical validity, diagnostic reliability, HIPAA compliance. **Always** display the persistent banner: "For research and testing purposes only. Not clinically validated." on every screen.

---

## 2. Original problem statement

> Create a privacy-preserving synthetic healthcare data platform that generates realistic patient cohorts for testing and validating digital health applications without exposing real patient information. The system should use a small sample healthcare dataset to generate larger synthetic patient records while maintaining realistic relationships between variables such as age, blood pressure, activity levels, medication adherence, and pain scores over time. Users should be able to define cohort requirements, such as increasing the proportion of older or diabetic patients, and generate customized datasets accordingly. The solution should also compare the generated data with the original sample using statistical validation techniques to measure its accuracy and consistency, and provide a dashboard for viewing patient trends, data distributions, validation results, and exporting the generated synthetic cohort for further testing.

---

## 3. Feature scope

**MUST HAVE:** CSV/Excel upload · Dataset Sparsity module (source-level) · Population profiling · Cohort request form · Feasibility Engine (request-level) · GaussianCopula generation · Synthetic Sanity checks · "Why Trust This?" screen (Feasibility/Quality/Privacy/Distribution-Correlation panels) · CSV/Excel export · disclaimer banner

**SHOULD HAVE:** PARSynthesizer (90-min checkpoint) + trajectory-bootstrapping fallback · TSTR utility validation · SPSS/Stata upload

**NICE TO HAVE:** Multi-model comparison toggle

**DO NOT BUILD:** Custom GAN, custom membership-inference implementation, "Purpose-Aware Generation" branching, real-time multi-user features, any HIPAA claim, unbounded "constraint engine"

---

## 4. THE DEMO DATASET (already built — `demo_patients.csv`, included alongside this doc)

500 patients × 6 months = 3,000 rows. Use this as the default/example dataset for every module's development and testing.

**Schema:**
```
patient_id            int, 1-500
month                  int, 1-6
age                    int
diabetic               int, 0 or 1
systolic_bp            float (2.9% missing — realistic structured missingness)
activity_steps         int
medication_adherence_pct  float (7.7% missing)
pain_score              float, 0-10
```

**Baseline subgroup counts (engineered deliberately — use these to verify your module's output, not just eyeball it):**
| Subgroup | Count | Expected Feasibility tier |
|---|---|---|
| Diabetic | 100 (20.0%) | **Strong** |
| Age > 65 | 90 (18.0%) | **Strong** |
| Diabetic + Age > 65 | 25 | **Moderate** |
| Diabetic + Age > 65 + Low adherence (<40%) | 2 | **Sparse** |

**Real correlations at month 6 (use these as the "source" baseline values throughout — synthetic output should land close to these, not identical):**
| Relationship | Value |
|---|---|
| Activity ↔ Pain | -0.56 |
| Adherence ↔ Pain | -0.30 |
| Age ↔ BP | 0.54 |
| Diabetic ↔ BP | 0.50 |

This dataset is the ground truth for every acceptance test in §9.

---

## 5. User flow

```
UPLOAD (CSV/Excel)
   ↓
DATASET SPARSITY  ← source-level, computed once
   ↓
POPULATION PROFILE
   ↓
COHORT DESIGNER (request form)
   ↓
FEASIBILITY GATE  ← request-level, computed per request
   ↓ (Sparse → block auto-proceed, require explicit confirmation)
GENERATION (GaussianCopula + PARSynthesizer/bootstrapping for temporal fields)
   ↓
SYNTHETIC SANITY CHECK
   ↓
WHY TRUST THIS?  ← Feasibility / Quality / Privacy / Distribution-Correlation panels
   ↓
EXPORT (CSV/Excel)
```

---

## 6. Module contracts (exact function signatures — build to these, not approximations)

### `data_ingest.py` — Agent 1
```python
def load_dataset(file_path: str) -> pd.DataFrame:
    """Accepts .csv, .xlsx. Raises ValueError with a clear message on
    unsupported format or unreadable file. Infers dtypes; does not assume
    column names beyond what's needed for downstream modules to detect
    (age, diabetic-like binary columns, a month/time column if present)."""

def detect_schema(df: pd.DataFrame) -> dict:
    """Returns: {'numeric_cols': [...], 'categorical_cols': [...],
    'binary_cols': [...], 'time_col': str or None,
    'patient_id_col': str or None}"""
```

### `sparsity.py` — Agent 1
```python
def compute_sparsity(df: pd.DataFrame, key_dims: list[str]) -> dict:
    """key_dims: e.g. ['diabetic', 'age_over_65', 'low_adherence'] — binary
    or bucketed conditions to check combinations of.
    Returns:
    {
      'record_count': int,
      'missingness': {col: {'pct': float, 'bucket': 'LOW'|'MODERATE'|'HIGH'}},
      'duplicates': {'count': int, 'bucket': str},
      'subgroup_counts': {frozenset of condition tuples -> int},
        # must include every combination of 1, 2, and 3 key_dims
      'rare_subgroups': [ (conditions, count) for count < 10 ],
      'temporal_completeness': float or None
    }
    Test against demo_patients.csv: subgroup_counts for
    ('diabetic',) must equal 100, ('diabetic','age_over_65') must equal 25,
    ('diabetic','age_over_65','low_adherence') must equal 2.
    """
```

### `feasibility.py` — Agent 2
```python
def classify_support(count: int) -> str:
    """n>=30 -> 'Strong', 10-29 -> 'Moderate', 3-9 -> 'Weak', <3 -> 'Sparse'"""

def evaluate_cohort_request(request: dict, sparsity_output: dict) -> dict:
    """request schema (see §7 below).
    Returns:
    {
      'per_combination': [
        {'conditions': [...], 'source_count': int, 'tier': str,
         'source_pct': float, 'target_pct': float}
      ],
      'overall_tier': str,  # the WEAKEST tier among all combinations
      'requires_confirmation': bool,  # True if overall_tier == 'Sparse'
      'target_achievement': None  # filled in post-generation, see shift.py
    }
    Test against demo_patients.csv with a request of
    {diabetic: 60%, age_over_65: 50%, low_adherence: 40%}:
    must return overall_tier == 'Sparse', requires_confirmation == True,
    driven by the diabetic+65+low_adherence combination (source_count=2).
    """
```

### `shift.py` — Agent 2
```python
def compute_population_shift(source_df, request: dict, generated_df) -> pd.DataFrame:
    """Returns a DataFrame with columns [variable, source_pct, target_pct,
    generated_pct] — one row per requested variable. This is the
    'Population Shift' table, NOT called 'Cohort Drift'."""

def target_achievement(request: dict, generated_df) -> dict:
    """Returns {variable: {'target': float, 'generated': float,
    'achieved': bool}} — 'achieved' if within 2 percentage points."""
```

### `generation.py` — Agent 3
```python
def generate_cross_sectional(source_df, request: dict, n_rows: int) -> pd.DataFrame:
    """Primary path: SDV GaussianCopulaSynthesizer, conditioned on request."""

def generate_longitudinal(source_df, synthetic_baseline_df, time_col: str) -> pd.DataFrame:
    """Plan A: SDV PARSynthesizer. HARD CHECKPOINT: if not producing stable,
    plausible output (no NaN explosions, no out-of-range values, visually
    sane trends) within 90 minutes of starting, STOP and switch to:
    Plan B: bootstrap_trajectories() below. Do not keep tuning past checkpoint."""

def bootstrap_trajectories(source_df, synthetic_baseline_df, time_col: str) -> pd.DataFrame:
    """Fallback: for each synthetic baseline patient, find the most similar
    real patient (nearest-neighbor on baseline attributes), resample that
    real patient's month-to-month DELTAS (not absolute values) onto the
    synthetic patient's baseline. Document this exact method in the pitch:
    'resamples observed longitudinal change patterns from similar real
    patients onto synthetic baseline patients.'"""
```

### `sanity.py` — Agent 4
```python
def run_sanity_checks(generated_df, schema: dict, source_df) -> dict:
    """Returns {check_name: {'passed': bool, 'detail': str}} for:
    valid_ranges (age, BP, pain_score within source min/max +/- 10%),
    no_duplicate_ids, valid_types, no_negative_values_where_inapplicable.
    Mechanical checks ONLY — do not imply clinical validity."""
```

### `validation.py` — Agent 4
```python
def compute_quality_metrics(source_df, generated_df) -> dict:
    """Wraps SDV/SDMetrics quality report. Returns column shape similarity
    scores, column-pair correlation trends, AND the raw correlation numbers
    (source vs synthetic) for the 'What did the model learn' table —
    reuse the 4 relationships in §4 as the reference set."""

def compute_privacy_metrics(source_df, generated_df) -> dict:
    """Wraps SDV/SDMetrics privacy/diagnostic report. MUST return the
    underlying number, never just a label — e.g.
    {'label': 'LOW', 'metric_name': 'distance_to_closest_record',
    'value': 0.34, 'interpretation': str}"""

def compute_missingness_similarity(source_df, generated_df) -> dict:
    """Compare missingness rates per column, source vs generated.
    Verify SDMetrics has this function before committing; if unavailable,
    implement as a simple side-by-side % comparison."""

def compute_tstr(source_df, generated_df, target_col: str) -> dict:
    """SHOULD HAVE. Train a simple model (e.g. logistic/linear regression)
    on synthetic data, test on held-out real data; compare to a real-trained
    baseline. Only attempt after MUST HAVE items are done."""
```

### `app.py` — Human integrator (you)
```python
"""Streamlit UI. Owns st.session_state for the full wizard flow:
upload -> sparsity -> cohort request -> feasibility -> generate -> sanity
-> trust screen -> export.
CRITICAL: Streamlit reruns the entire script on every interaction. Every
piece of state that must survive a rerun (uploaded df, sparsity output,
current request, generated df, validation results) MUST live in
st.session_state, not local variables.
Persistent disclaimer banner on every screen.
Plotly for all charts (KDE overlays, correlation heatmaps, box/violin).
Palette: muted blues/grays. Monospace font for numeric values."""
```

---

## 7. Cohort request schema (exact contract between UI and Feasibility Engine)

```python
request = {
    "target_n": 10000,                     # desired synthetic cohort size
    "conditions": [
        {"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 60},
        {"variable": "age", "operator": ">", "value": 65, "target_pct": 50},
        {"variable": "medication_adherence_pct", "operator": "<", "value": 40, "target_pct": 40},
    ]
}
```
The Feasibility Engine evaluates every individual condition AND every 2-way/3-way combination among `conditions`.

---

## 8. "Why Trust This?" screen — panel contents

1. **Feasibility panel** — per-combination table from `feasibility.py`, Target Achievement vs. Source Evidence shown as two distinct rows, never merged
2. **Quality panel** — SDMetrics quality scores + the 4-relationship "what did the model learn" table (§4 reference values), labeled "observed statistical associations, not causal relationships"
3. **Privacy panel** — always paired number + label, never a bare adjective
4. **Distribution/Correlation panel** — Plotly KDE overlays (source vs. synthetic) for BP, activity, adherence, pain; correlation heatmap side-by-side

---

## 9. Acceptance tests (run these against `demo_patients.csv` — if they pass, the module is done)

| Module | Test | Expected result |
|---|---|---|
| `sparsity.py` | `compute_sparsity()` on demo data, key_dims=[diabetic, age_over_65, low_adherence] | diabetic count=100, diabetic+age_over_65 count=25, triple combo count=2 |
| `feasibility.py` | Request: diabetic 60%, age>65 50%, low_adherence 40% | `overall_tier == 'Sparse'`, `requires_confirmation == True` |
| `feasibility.py` | Request: diabetic 30% only | `overall_tier == 'Strong'` (source count 100 >= 30) |
| `validation.py` | `compute_quality_metrics()` on demo data vs. any generated copy | Returned correlation values within reasonable range of §4 reference values (Activity↔Pain ≈ -0.56, etc.) |
| `app.py` | Full upload→export click-through | No state loss on any rerun; disclaimer banner visible on every screen |

---

## 10. Demo script (3–5 min)

1. **Hook (15s):** "Clinical researchers need realistic patient data, but real data is locked behind privacy — and existing platforms assume millions of records. What if you only have 500?"
2. **Upload + Sparsity (30s):** show sparsity summary live on `demo_patients.csv`
3. **Cohort request (30s):** request diabetic 60% / age>65 50% / low adherence 40% — the engineered Sparse case
4. **Wow moment (45s):** Feasibility gate flags it Sparse (source count: 2) before generating — slow down here
5. **Generate + Why Trust This (60s):** walk all four panels
6. **Close (20s):** positioning statement from §1

---

## 11. Naming candidates
**Cohortly** · **Verita Health** · **SynthCase**

---

## 12. Team assignment
- **Agent 1** (Person A supervises): `data_ingest.py` + `sparsity.py`
- **Agent 2** (Person B supervises): `feasibility.py` + `shift.py`
- **Agent 3** (Person C supervises): `generation.py`, including the 90-min PARSynthesizer checkpoint decision
- **Agent 4** (Person D supervises): `sanity.py` + `validation.py`
- **You:** `app.py` integration + final wiring + demo rehearsal

**Instruction to give Antigravity verbatim for the Streamlit build:** "This app has a multi-step wizard flow. Streamlit reruns the entire script on every interaction — use `st.session_state` explicitly to persist state across steps. Do not build this as a naive linear script."

## 13. Visual/frontend design spec

- Palette: muted blues/grays — closer to a bioinformatics dashboard or journal figure than a consumer app gradient
- Numbers/statistics rendered in a monospace font
- Charts via **Plotly**, not default Streamlit charts — specifically: KDE distribution overlays, correlation heatmaps, box/violin plots for subgroup comparison
- The "Why Trust This?" screen (§6) is a structured report layout (labeled panels/sections), not a loose dashboard grid
- Persistent disclaimer banner on every screen: "For research and testing purposes only. Not clinically validated."

---