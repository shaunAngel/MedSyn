# MedSyn

**Synthetic clinical data generation with a validation firewall.**

MedSyn generates realistic synthetic patient cohorts from a small real dataset, then measures whether that synthetic data is actually *useful* and actually *private* — instead of assuming both.

> **Core premise: synthetic does not automatically mean private.**
>
> Generative models memorise their training data. A synthetic dataset can still leak information about the real patients it was trained on, through membership inference, nearest-neighbour similarity, and rare-combination disclosure. Most synthetic-data tooling asks you to take privacy on faith. MedSyn measures it.

Built for VNRVJIET Hackathon 2026 — Problem Statement **SH-405**, *Synthetic Patient Data Generation for Clinical Research*.

---

## What this is

A generator is one component of MedSyn, not the product. The product is the loop around it:

```text
                 SOURCE HEALTHCARE DATA (small, real)
                              |
                              v
                     +--------------------+
                     |  Dataset Profiler  |
                     |  schema, ranges    |
                     |  distributions     |
                     |  correlations      |
                     +---------+----------+
                               |
                               v
                     +--------------------+
                     | Generation Engine  |
                     |  SDV baseline      |
                     +---------+----------+
                               |
                               v
                     +--------------------+
                     |  Cohort Compiler   |
                     |  target conditions |
                     +---------+----------+
                               |
                               v
             +---------------------------------+
             |       VALIDATION FIREWALL       |
             |                                 |
             |   Fidelity   Utility   Privacy  |
             |              (TSTR)    (audit)  |
             +----------------+----------------+
                              |
                              v
                     Validation Report
                              |
                              v
                   Synthetic Cohort Export
```

Nothing leaves the pipeline without a validation report attached.

---

## Scope

### In scope — core build

| Module | What it does |
|---|---|
| **Dataset Profiler** | Schema, missingness, ranges, distributions, correlation matrix, candidate quasi-identifiers |
| **Generation Engine** | Tabular synthesis via SDV (GaussianCopula / CTGAN / TVAE), preserving inter-variable relationships |
| **Cohort Compiler** | User-specified population requirements → conditional generation |
| **Fidelity Validation** | Distribution, correlation, and higher-order structure comparison against source |
| **TSTR Utility** | Train-on-Synthetic, Test-on-Real vs. a real-trained baseline |
| **Privacy Audit** | Duplicate detection, nearest-neighbour similarity, rare-combination risk, membership inference |

### Roadmap — not yet implemented, not claimed

- Differential privacy generation path with a formal privacy budget (ε)
- Privacy–utility–fidelity frontier explorer
- Clinical plausibility constraint engine
- Longitudinal patient trajectory generation
- Natural-language cohort builder
- Edge-case / stress cohort mode

These are deliberately listed as future work. MedSyn does **not** currently make differential-privacy guarantees.

---

## Why validation is the product

### Fidelity is necessary but not sufficient

Overlapping histograms are the weakest possible evidence. Synthetic data can match means and correlations while breaking high-order structure — rare combinations, conditional relationships, subgroup behaviour. It looks right in charts and fails as training data.

So MedSyn reports distribution fidelity, correlation fidelity, and higher-order structure separately, and does not collapse them into a single "quality score."

### TSTR is the utility test that matters

```text
   Train on SYNTHETIC  ──►  Test on held-out REAL   ──┐
                                                       ├──►  compare
   Train on REAL       ──►  Test on held-out REAL   ──┘
```

If a model trained purely on synthetic data performs close to one trained on real data, the synthetic cohort has retained genuinely useful predictive structure. That is a substantive claim. Matching histograms is not.

TSTR results are dataset- and task-specific and are reported as such.

### The privacy audit attacks our own generator

```text
Privacy Risk Audit

Exact duplicates            [ measured ]
High-similarity records     [ measured ]
Rare-combination risk       [ measured ]
Membership inference        [ measured ]
```

A membership inference attack tries to determine whether a specific real record was in the generator's training set. An attack accuracy near 50% means the attacker is guessing. Meaningfully above 50% means information is leaking.

We run this attack against ourselves and publish the result, whatever it says.

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI |
| Generation | SDV (GaussianCopula, CTGAN, TVAE) |
| Evaluation | scikit-learn, SciPy |
| Data | pandas, NumPy |
| Frontend | React + Vite (Streamlit for early prototyping) |

---

## Repository structure

```text
MedSyn/
├── backend/
│   ├── api/                 # FastAPI routes
│   ├── profiling/           # dataset profiler
│   ├── generation/          # SDV wrappers, conditional sampling
│   ├── cohort/              # cohort spec parsing and compilation
│   ├── validation/          # fidelity + TSTR
│   └── privacy/             # duplicate, NN, rare-combo, membership inference
│
├── frontend/
│   ├── components/
│   ├── pages/
│   └── services/
│
├── experiments/
│   ├── baseline/
│   ├── tstr/
│   └── privacy/
│
├── data/                    # see data/README.md — no raw data committed
├── reports/                 # generated validation reports
├── tests/
├── requirements.txt
└── README.md
```

**No raw or private datasets are committed to this repository.**

---

## Getting started

```bash
git clone https://github.com/shaunAngel/MedSyn.git
cd MedSyn

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Run the API:

```bash
uvicorn backend.api.main:app --reload
```

Run the end-to-end baseline pipeline:

```bash
python -m experiments.baseline.run --input data/sample.csv --n 10000
```

---

## Results

> Populated from actual experiment runs. No placeholder or estimated values.

| Metric | Source data | Synthetic | Notes |
|---|---|---|---|
| Distribution fidelity | — | — | to be filled |
| Correlation fidelity | — | — | to be filled |
| TSTR — accuracy | — | — | to be filled |
| TSTR — ROC-AUC | — | — | to be filled |
| Exact duplicates | — | — | to be filled |
| Membership inference accuracy | — | — | 50% = no leakage |

Reproduce with the commands in `experiments/`.

---

## Limitations

Stated plainly, because the alternative is worse:

- MedSyn does **not** claim differential privacy. No formal privacy guarantee is currently provided.
- Privacy audit results reflect **the specific attacks implemented here**. Resistance to these attacks is not resistance to all attacks.
- Fidelity and utility metrics are **specific to the evaluated dataset and task** and do not generalise.
- Synthetic output is **not clinically validated** and is not a substitute for real patient data in clinical decision-making.
- No clinical plausibility constraint layer is implemented yet, so statistically plausible but clinically impossible records are possible.

---

## Team

Shaun · Abhilash · Shiva Sai
VNRVJIET — Computer Science and Business Systems
