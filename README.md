# Synora

### Synthetic patient cohorts for research teams who don't have millions of records.

**Synora** is a research-focused synthetic patient cohort platform that helps teams generate structured synthetic healthcare data while providing evidence about **cohort feasibility, statistical fidelity, utility, and privacy risk**.

Instead of treating synthetic data generation as a black box, Synora puts a decision and evidence layer around the process:

**SOURCE → TARGET → SYNTHETIC**

> **For research and testing purposes only. Not clinically validated.**

---

## Why Synora?

Healthcare research and digital-health development often depend on patient-level data, but access to real-world datasets can be restricted, expensive, or difficult to scale.

Even when a dataset is available, there is another problem:

**Can the dataset actually support the cohort you want to generate?**

A researcher may have 500 patients and request a synthetic cohort of 10,000 patients with a highly specific combination of conditions. A generator can produce rows — but that does not automatically mean the requested population was well-supported by the source data.

Synora makes this question explicit **before generation** and evaluates the resulting synthetic cohort **after generation**.

---

## What Synora Does

### 1. Dataset Sparsity Analysis

Synora profiles the uploaded source dataset and identifies how strongly different patient subgroups are represented.

It evaluates:

* Individual cohort conditions
* 2-way combinations
* 3-way combinations
* Observed subgroup counts
* Missingness patterns

Subgroups are classified as:

**Strong → Moderate → Weak → Sparse**

The overall feasibility assessment is governed by the weakest relevant subgroup.

This means researchers can see when a requested cohort requires significant extrapolation from limited source evidence.

---

### 2. Cohort Designer

Researchers define the population they want to generate using conditions such as:

```text
Diabetic = 60%
Age > 65 = 50%
Medication adherence < 40% = 40%
```

Synora evaluates whether the source dataset provides meaningful evidence for that requested population.

Sparse combinations trigger an explicit confirmation step rather than silently proceeding.

---

### 3. Synthetic Cohort Generation

Once the cohort request is reviewed, Synora generates the requested synthetic population.

The current prototype uses **SDV's Gaussian Copula Synthesizer** for structured tabular generation.

We deliberately treat the generator as the **generation layer**, not the core innovation.

> **Our differentiation is the evidence and decision layer around synthetic data generation.**

For longitudinal data, the prototype also supports trajectory-oriented generation using observed patient-level changes.

---

### 4. Statistical Validation

Synora does not reduce synthetic-data quality to a single "accuracy" number.

It compares the source and generated populations across multiple dimensions:

* Distribution similarity
* Variable relationships and correlations
* Missingness patterns
* Target cohort proportions
* Automated SDV/SDMetrics quality measures

Example observed relationships can include:

```text
Age ↔ Blood Pressure
Diabetes ↔ Blood Pressure
Activity ↔ Pain
Medication Adherence ↔ Pain
```

These are evaluated as **observed statistical associations, not causal relationships**.

---

### 5. Privacy Risk Evaluation

Synora includes an empirical **membership-inference attack** to test whether records from the training split can be distinguished from held-out records using their proximity to generated records.

The prototype evaluates:

* Nearest synthetic-record distance
* Distance-based membership classification
* Attack AUROC

The privacy panel makes the methodology visible rather than hiding it behind a proprietary score.

> **A near-random membership-inference result is evidence against this particular attack succeeding — it is not a formal privacy guarantee.**

Synora therefore does **not** claim differential privacy, anonymization guarantees, or comprehensive privacy protection.

---

### 6. Population Explorer

Researchers can explore the generated population through:

* Demographic distributions
* Clinical-variable distributions
* Cohort composition
* Relationship visualizations
* Generated population statistics

The goal is to make the synthetic cohort inspectable rather than treating the exported CSV as the end of the workflow.

---

## Product Flow

```text
UPLOAD
   ↓
DATASET SPARSITY
   ↓
POPULATION PROFILE
   ↓
COHORT DESIGNER
   ↓
FEASIBILITY GATE
   ↓
GENERATION
   ↓
SYNTHETIC SANITY
   ↓
WHY TRUST THIS?
   ↓
POPULATION EXPLORER
   ↓
EXPORT
```

The central product principle is:

> **Don't just generate synthetic data. Show researchers why they should trust what they generated — and where they shouldn't.**

---

## Example

Imagine a researcher has a source dataset containing:

```text
500 patients
6 months of observations
3,000 longitudinal records
```

The researcher requests:

```text
10,000 synthetic patients

60% diabetic
50% age > 65
40% medication adherence < 40%
```

The source dataset may contain thousands of examples for individual characteristics while containing only **2 patients** matching the full three-way combination.

A conventional generator can still produce the requested cohort.

Synora surfaces the evidence gap first:

```text
Diabetic                         → Strong
Age > 65                        → Strong
Diabetic + Age > 65             → Moderate
Full requested combination      → Sparse
```

The researcher can then make an informed decision about whether to proceed.

---

## Architecture

At a high level:

```text
                 ┌─────────────────────┐
                 │   Researcher Input  │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Dataset Profiling   │
                 │ & Sparsity Engine   │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Cohort Feasibility  │
                 │       Gate          │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Synthetic Generation│
                 │       Layer         │
                 └──────────┬──────────┘
                            ↓
          ┌─────────────────┼─────────────────┐
          ↓                 ↓                 ↓
   Statistical          Utility          Privacy
   Validation          Evaluation        Evaluation
          └─────────────────┼─────────────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Population Explorer │
                 │     & Export        │
                 └─────────────────────┘
```

### Core evaluation dimensions

**Fidelity**
Does the synthetic population preserve important statistical properties of the source?

**Utility**
Can the synthetic population support downstream research/testing tasks?

**Privacy**
Can a specific empirical attack distinguish training membership?

These dimensions are evaluated separately rather than collapsed into a single trust score.

---

## Technical Stack

### Frontend

* **React 19**
* **Vite**
* **Tailwind CSS**
* **Recharts**
* **Lucide React**
* **Canvas Confetti**

### Generation & Evaluation

The prototype architecture is designed around:

* **SDV**
* **SDMetrics**
* Statistical distribution and correlation comparisons
* Cohort feasibility analysis
* Membership-inference evaluation
* Train/Test-on-Synthetic-style utility evaluation

---

## Project Structure

```text
Synora/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   ├── services/
│   ├── views/
│   ├── App.jsx
│   ├── App.css
│   ├── index.css
│   └── main.jsx
├── .gitignore
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
└── README.md
```

---

## Running Locally

### Prerequisites

* Node.js
* npm

### Installation

Clone the repository:

```bash
git clone https://github.com/shaunAngel/Synora.git
cd Synora
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

Run linting:

```bash
npm run lint
```

---

## Current Prototype Scope

Synora is currently a **research/hackathon prototype** demonstrating the product workflow and decision/evidence layer around synthetic patient cohort generation.

The prototype focuses on:

* Structured patient datasets
* Cohort feasibility
* Synthetic generation
* Statistical comparison
* Population exploration
* Empirical privacy-risk evaluation

It is not intended to replace clinical validation, regulatory review, privacy audits, or domain-expert assessment.

---

## Important Limitations

Synora does **not** claim:

* Clinical validity
* Diagnostic reliability
* HIPAA compliance
* Formal differential privacy
* Guaranteed anonymization
* Complete privacy protection
* Causal inference from observed correlations

The feasibility thresholds used by Synora are **product-level evidence heuristics**, not universal statistical laws.

Similarly, privacy evaluation represents a specific empirical attack surface rather than a comprehensive privacy assessment.

---

## Vision

The long-term vision for Synora is to make synthetic healthcare data more **inspectable, evidence-driven, and usable for research and software testing**.

The core idea is simple:

> **Synthetic data should not arrive with a black box. It should arrive with evidence.**

---

## Disclaimer

**Synora is intended for research and testing purposes only. It is not clinically validated and should not be used for diagnosis, treatment, or clinical decision-making.**
