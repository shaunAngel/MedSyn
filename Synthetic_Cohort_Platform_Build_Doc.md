# Synthetic Patient Cohort Platform — Build Documentation

**For: Antigravity agent-assisted build**
**Hackathon time remaining: ~20 hours from doc creation**
**Team: 4 members, 1 module per agent + 1 human integrator**

---

## 1. Product thesis (read this first — it governs every design decision below)

> SDV/SDMetrics already generate and evaluate synthetic tabular data. **Our product is the decision layer**: before generation, it tells a researcher whether their requested cohort is actually supported by evidence in their source data; after generation, it explains what was preserved, what was intentionally changed, and where the system had to extrapolate — in language a clinical researcher can act on, not an ML engineer.

**Positioning statement:** Synthetic patient cohorts for research teams who don't have millions of records — generated, checked, and proven trustworthy before you download a single row.

**Never claim:** clinical accuracy, medical validity, diagnostic reliability, HIPAA compliance (unless substantiated), safety for real patient care.

**Always claim, when true:** "preserves selected statistical relationships observed in the source data," "passed our defined validity checks," "privacy risk evaluated using established distance-based metrics," "not validated for clinical accuracy — for research and testing use only."

A persistent, visible disclaimer banner ("For research and testing purposes only. Not clinically validated.") is a MUST HAVE UI element, present on every screen.

---

## 2. Original problem statement

> Create a privacy-preserving synthetic healthcare data platform that generates realistic patient cohorts for testing and validating digital health applications without exposing real patient information. The system should use a small sample healthcare dataset to generate larger synthetic patient records while maintaining realistic relationships between variables such as age, blood pressure, activity levels, medication adherence, and pain scores over time. Users should be able to define cohort requirements, such as increasing the proportion of older or diabetic patients, and generate customized datasets accordingly. The solution should also compare the generated data with the original sample using statistical validation techniques to measure its accuracy and consistency, and provide a dashboard for viewing patient trends, data distributions, validation results, and exporting the generated synthetic cohort for further testing.

---

## 3. Final feature scope

### MUST HAVE
- File upload: CSV, Excel (.xlsx)
- **Dataset Sparsity module** (source-level, computed once at upload — see §5.1)
- Population profiling (dtypes, distributions, correlations, missingness %)
- Cohort request form (structured filters: % diabetic, % over age X, adherence level, etc.)
- **Feasibility Engine** (request-level, computed per cohort request — see §5.2)
- Generation via SDV GaussianCopula (primary method)
- Synthetic Sanity pre-flight checks (valid ranges, no duplicate IDs, valid types)
- **"Why Trust This?" screen** with four labeled panels: Feasibility, Quality, Privacy, Distribution/Correlation comparisons (see §6)
- CSV/Excel export
- Persistent disclaimer banner

### SHOULD HAVE
- PARSynthesizer attempt for longitudinal/temporal data, with a hard time-boxed checkpoint (see §7)
- Trajectory-bootstrapping fallback if PARSynthesizer checkpoint fails
- **TSTR (Train-Synthetic-Test-Real) utility validation** — promoted from Nice-to-Have
- SPSS (.sav) / Stata (.dta) upload support via `pyreadstat`
- Basic real-vs-synthetic trajectory chart

### NICE TO HAVE
- Multi-model comparison toggle (Copula vs CTGAN vs TVAE)

### DO NOT BUILD
- Custom GAN from scratch
- Custom membership-inference attack implementation (use SDV/SDMetrics built-ins)
- "Purpose-Aware Generation" branching UI
- Real-time multi-user dashboard
- Any HIPAA compliance claim
- A giant free-form "Constraint Engine" — hard-coded range checks only

---

## 4. User flow

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
   ↓ (if Sparse/Weak: require explicit "generate anyway" confirmation)
GENERATION (GaussianCopula, + PARSynthesizer/bootstrapping for temporal fields)
   ↓
SYNTHETIC SANITY CHECK (pre-flight, mechanical)
   ↓
WHY TRUST THIS?  ← Feasibility / Quality / Privacy / Distribution-Correlation panels
   ↓
EXPORT (CSV/Excel)
```

---

## 5. Core algorithms (implement exactly as specified — do not let the agent improvise the methodology)

### 5.1 Dataset Sparsity module (source-level, `sparsity.py`)

Computed once, immediately after upload. Independent of any cohort request.

Outputs:
- Record count
- Missingness % per column → bucketed: LOW (<5%), MODERATE (5-20%), HIGH (>20%)
- Duplicate record count/% → bucketed: LOW/MODERATE/HIGH
- Rare subgroup detection: for the key clinical dimensions (diabetes, age bracket, adherence tier — configurable), enumerate 2-way and 3-way combinations and flag any combination with **n < 10** as a rare subgroup, listing exact counts
- Temporal completeness (if a time/sequence column exists): % of patients with complete observation sequences vs. gaps

Display as a compact summary card immediately after upload, before the researcher does anything else.

### 5.2 Feasibility Engine (request-level, `feasibility.py`)

Computed fresh on every cohort request submission.

**Algorithm:**
1. Parse the requested cohort into discrete conditions (e.g., diabetic=yes, age>65, adherence=low)
2. For each individual condition AND each combination of conditions requested together, query the Dataset Sparsity module's precomputed subgroup counts for the matching real-record count
3. Classify by fixed thresholds:
   - n ≥ 30 → **Strong**
   - 10–29 → **Moderate**
   - 3–9 → **Weak**
   - <3 → **Sparse / Extrapolative**
4. If the lowest-supported combination is Sparse, **block auto-proceed** — require explicit user confirmation ("Generate anyway" / "Modify request" / "View source support detail") before generation proceeds
5. Display per-combination, not just an overall score — granularity is the point

**Explicitly separate two concepts, computed and displayed distinctly (do not merge into one metric):**
- **Target Achievement:** did the generator actually hit the requested proportion? (e.g., "Target diabetic: 60%, Generated: 60% ✓")
- **Source Evidence:** how well does the *source* data actually support that target? (e.g., "Source diabetic: 20% — HIGH EXTRAPOLATION")

A generator can succeed at (1) while (2) is poor. Never let the UI imply that hitting the target proves the request was well-supported.

### 5.3 Population Shift table (`shift.py`, reuses feasibility + generation outputs)

Three-column comparison, per requested variable:

| | Source | Target | Generated |
|---|---|---|---|
| Diabetes | 22% | 50% | 49.8% |

This answers three distinct questions in one table: did we satisfy the request (Target vs. Generated), how much did the researcher intentionally shift the population (Source vs. Target), and did the model successfully realize that shift (Target vs. Generated again, framed as accuracy).

Naming: call this **"Population Shift,"** not "Cohort Drift" (drift implies unintended change; this change is deliberate).

---

## 6. "Why Trust This?" screen — exact spec

Four labeled panels, in this order. This is the product's core credibility moment — allocate the most frontend polish here.

1. **Feasibility panel** — pulls directly from §5.2: per-combination support level (Strong/Moderate/Weak/Sparse), with the Target Achievement vs. Source Evidence distinction shown explicitly, not collapsed into one number
2. **Quality panel** — SDV/SDMetrics quality report output: column shape similarity, column-pair correlation trends. Include the "What did the model learn?" associations table (observed statistical associations in source vs. synthetic — e.g., Activity↔Pain: -0.48 vs -0.45), explicitly labeled "observed statistical associations, not causal relationships"
3. **Privacy panel** — SDV/SDMetrics privacy/diagnostic metrics (distance-to-closest-record and/or membership-inference-style scoring, whichever SDMetrics ships natively — do not hand-roll this). **Never display a bare label** ("Privacy risk: LOW") — always pair with the underlying number ("LOW — nearest-neighbor distance well above duplication threshold" or equivalent)
4. **Distribution/Correlation comparison panel** — real vs. synthetic overlaid distributions (Plotly KDE plots) for key numeric variables, plus a real vs. synthetic correlation heatmap side-by-side

---

## 7. Longitudinal/temporal generation — decision protocol

**Plan A:** Attempt `SDV.sequential.PARSynthesizer` on the temporal fields (BP, pain score, adherence over time), using patient demographics as context columns.

**Hard checkpoint:** if PARSynthesizer is not producing plausible, stable output within **90 minutes** of starting this task, stop and pivot — do not keep tuning past this checkpoint.

**Plan B (fallback, pre-approved, not a last-minute scramble):** Trajectory bootstrapping — generate synthetic baseline patients via GaussianCopula, then resample observed real month-to-month **change patterns** (deltas, not absolute values) from similar real patients onto those synthetic baselines. Framing for the pitch: "we resample observed longitudinal change patterns from similar real patients onto synthetic baseline patients, rather than claiming to mechanistically model disease progression."

Decide who owns this task and confirm the 90-minute checkpoint time on the clock right now, as a team, before starting.

---

## 8. Technical architecture

```
/data_ingest.py      — CSV/Excel/(SPSS/Stata) upload, dtype inference
/sparsity.py          — §5.1, source-level sparsity + rare subgroup detection
/feasibility.py        — §5.2, request-level feasibility engine
/shift.py             — §5.3, Population Shift table
/generation.py        — GaussianCopula (primary) + PARSynthesizer/bootstrapping (temporal)
/sanity.py            — pre-flight mechanical checks (ranges, dupes, IDs, types)
/validation.py        — SDV/SDMetrics quality + privacy + missingness-similarity wrapper
/app.py                — Streamlit UI, owns st.session_state wizard flow, integrates all modules
```

**Module ownership (map to your 4 agents + yourself as integrator):**
- Agent 1: `data_ingest.py` + `sparsity.py`
- Agent 2: `feasibility.py` + `shift.py`
- Agent 3: `generation.py` (including the Plan A/B temporal decision)
- Agent 4: `sanity.py` + `validation.py`
- You: `app.py` integration, Streamlit `st.session_state` wizard flow, final wiring, demo rehearsal

**Explicit instruction to give Antigravity for the Streamlit build:** "Streamlit reruns the entire script on every user interaction. This app has a multi-step wizard flow (upload → sparsity → cohort request → feasibility → generate → sanity → trust screen → export). Use `st.session_state` explicitly to persist state across steps — do not build this as a naive linear script."

---

## 9. Visual/frontend design spec

- Palette: muted blues/grays — closer to a bioinformatics dashboard or journal figure than a consumer app gradient
- Numbers/statistics rendered in a monospace font
- Charts via **Plotly**, not default Streamlit charts — specifically: KDE distribution overlays, correlation heatmaps, box/violin plots for subgroup comparison
- The "Why Trust This?" screen (§6) is a structured report layout (labeled panels/sections), not a loose dashboard grid
- Persistent disclaimer banner on every screen: "For research and testing purposes only. Not clinically validated."

---

## 10. Demo script (3–5 min)

1. **Hook (15s):** "Clinical researchers need realistic patient data, but real data is locked behind privacy and governance — and existing platforms assume you already have millions of records. What if you only have 500?"
2. **Upload + Sparsity (30s):** show the sparsity summary appearing live
3. **Cohort request (30s):** request a deliberately sparse subgroup combination
4. **The wow moment (45s):** Feasibility gate flags it Sparse before generating — narrate this explicitly, this is the moment to slow down for
5. **Generate + Why Trust This (60s):** walk through the four panels, emphasize the Feasibility panel and Target-vs-Source distinction
6. **Close (20s):** state the positioning sentence directly (§1)

---

## 11. Naming candidates

- **Cohortly** — implies cohort-building as the core action
- **Verita Health** — implies trust/validation as the core value
- **SynthCase** — implies case/cohort + synthetic

---

## 12. Acceptance criteria (definition of done, per module)

- `sparsity.py`: given any uploaded CSV/Excel, returns missingness/duplicate/rare-subgroup buckets without crashing on missing columns
- `feasibility.py`: given a cohort request dict + sparsity output, returns per-combination Strong/Moderate/Weak/Sparse classification and blocks proceed on Sparse without explicit override
- `generation.py`: produces a synthetic dataset matching requested row count and schema; temporal fields present if Plan A or B succeeded, absent (with a clear note) if both failed
- `validation.py`: every displayed metric has a paired underlying number, never a bare adjective label
- `app.py`: full upload→export flow completable without state loss on any Streamlit rerun
