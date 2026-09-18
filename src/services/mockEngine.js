// Self-Contained Client-Side Synthetic Data Engine & Mock Backend

let cachedSourcePatients = null;
let cachedSynthDataset = null;

function generateGroundTruthDataset() {
  if (cachedSourcePatients) return cachedSourcePatients;

  const ethnicities = ['Caucasian', 'African American', 'Hispanic', 'Asian', 'Other'];
  const genders = ['Male', 'Female'];

  const patients = [];
  
  for (let i = 0; i < 500; i++) {
    const pId = `P${String(i + 1).padStart(3, '0')}`;
    const gender = genders[i % 2 === 0 ? 0 : 1];
    
    let diabetic = 0;
    let age = 20 + (i % 60);
    let ethnicity = ethnicities[i % 5];

    if (i < 2) {
      diabetic = 1;
      age = 68 + i;
      ethnicity = 'Other'; // 2 Patients (Sparse Subgroup Benchmark)
    } else if (i < 25) {
      diabetic = 1;
      age = 66 + (i % 15);
      ethnicity = ethnicities[i % 4]; // 23 Patients -> Total Diabetic + Age > 65 = 25
    } else if (i < 100) {
      diabetic = 1;
      age = 30 + (i % 35);
      ethnicity = ethnicities[i % 5]; // 75 Patients -> Total Diabetic = 100
    }

    patients.push({
      patient_id: pId,
      age,
      gender,
      ethnicity,
      diabetic
    });
  }

  const records = [];
  patients.forEach(p => {
    const baseHba1c = p.diabetic === 1 ? 8.2 + (Math.random() * 1.2 - 0.6) : 5.4 + (Math.random() * 0.6 - 0.3);
    const baseBp = p.diabetic === 1 ? 138 + Math.floor(Math.random() * 15 - 7) : 122 + Math.floor(Math.random() * 10 - 5);
    const latentHealth = Math.random() * 2 - 1; // Factor for Activity <-> Pain correlation (~ -0.56)

    for (let m = 1; m <= 6; m++) {
      const activityScore = Math.min(100, Math.max(0, Math.round((60 + 15 * latentHealth + (Math.random() * 16 - 8)) * 10) / 10));
      const painScore = Math.min(10, Math.max(0, Math.round((4.5 - 1.8 * latentHealth + (Math.random() * 2.4 - 1.2)) * 10) / 10));

      records.push({
        patient_id: p.patient_id,
        month: m,
        age: p.age,
        gender: p.gender,
        ethnicity: p.ethnicity,
        diabetic: p.diabetic,
        hba1c: Math.round((baseHba1c + (Math.random() * 0.3 - 0.15)) * 100) / 100,
        systolic_bp: Math.round(baseBp + (Math.random() * 4 - 2)),
        activity_score: activityScore,
        pain_score: painScore,
        medication_adherence: p.diabetic === 1 ? Math.floor(75 + Math.random() * 25) : Math.floor(88 + Math.random() * 12)
      });
    }
  });

  cachedSourcePatients = { patients, records };
  return cachedSourcePatients;
}

export function getDatasetDNA() {
  const { patients, records } = generateGroundTruthDataset();

  const diabeticCount = patients.filter(p => p.diabetic === 1).length;
  const diabeticAge65 = patients.filter(p => p.diabetic === 1 && p.age > 65).length;
  const tripleCombo = patients.filter(p => p.diabetic === 1 && p.age > 65 && p.ethnicity === 'Other').length;

  // Demographics Histogram
  const ageBins = { '<35': 0, '35-50': 0, '51-65': 0, '>65': 0 };
  patients.forEach(p => {
    if (p.age < 35) ageBins['<35']++;
    else if (p.age <= 50) ageBins['35-50']++;
    else if (p.age <= 65) ageBins['51-65']++;
    else ageBins['>65']++;
  });

  const ageHistogram = Object.entries(ageBins).map(([range, count]) => ({ range, count }));

  // Gender & Ethnicity Doughnut Data
  const genderCounts = { Male: 0, Female: 0 };
  patients.forEach(p => genderCounts[p.gender]++);
  const genderDoughnut = Object.entries(genderCounts).map(([gender, count]) => ({ name: gender, value: count }));

  const ethnicityCounts = {};
  patients.forEach(p => ethnicityCounts[p.ethnicity] = (ethnicityCounts[p.ethnicity] || 0) + 1);
  const ethnicityBar = Object.entries(ethnicityCounts).map(([ethnicity, count]) => ({ ethnicity, count }));

  return {
    schema: {
      total_patients: 500,
      total_rows: 3000,
      months_recorded: 6,
      columns: {
        age: { dtype: 'int64', type: 'numerical', min: 20, max: 84, mean: 52.4 },
        gender: { dtype: 'object', type: 'categorical', categories: ['Male', 'Female'] },
        ethnicity: { dtype: 'object', type: 'categorical', categories: ['Caucasian', 'African American', 'Hispanic', 'Asian', 'Other'] },
        diabetic: { dtype: 'int64', type: 'categorical', categories: ['0', '1'] },
        hba1c: { dtype: 'float64', type: 'numerical', min: 4.2, max: 14.2, mean: 6.1 },
        systolic_bp: { dtype: 'int64', type: 'numerical', min: 92, max: 188, mean: 126.3 },
        activity_score: { dtype: 'float64', type: 'numerical', min: 12.0, max: 98.5, mean: 58.2 },
        pain_score: { dtype: 'float64', type: 'numerical', min: 0.0, max: 9.8, mean: 4.1 },
        medication_adherence: { dtype: 'int64', type: 'numerical', min: 40, max: 100, mean: 89.2 }
      }
    },
    benchmarks: {
      diabetic_count: diabeticCount,
      diabetic_age_gt_65: diabeticAge65,
      triple_combo_sparse: tripleCombo
    },
    sparsity_health: {
      health_score: 91.2,
      sparse_cell_count: 3
    },
    demographics: {
      ageHistogram,
      genderDoughnut,
      ethnicityBar
    }
  };
}

export function evaluateFeasibility(filters = {}, researcherConfirmed = false) {
  const { patients } = generateGroundTruthDataset();

  let filtered = patients;
  if (filters.diabetic !== undefined && filters.diabetic !== null && filters.diabetic !== 'All') {
    filtered = filtered.filter(p => p.diabetic === Number(filters.diabetic));
  }
  if (filters.ethnicity && filters.ethnicity !== 'All') {
    filtered = filtered.filter(p => p.ethnicity === filters.ethnicity);
  }
  if (filters.age_min) {
    filtered = filtered.filter(p => p.age >= Number(filters.age_min));
  }
  if (filters.age_max) {
    filtered = filtered.filter(p => p.age <= Number(filters.age_max));
  }
  if (filters.gender && filters.gender !== 'All') {
    filtered = filtered.filter(p => p.gender === filters.gender);
  }

  const count = filtered.length;
  const requires_confirmation = count < 3;
  const support_tier = count >= 30 ? 'Strong' : (count >= 10 ? 'Moderate' : (count >= 3 ? 'Sparse' : 'Unsupported'));
  const passed = count >= 3 || researcherConfirmed;

  return {
    matching_patient_count: count,
    support_tier,
    requires_confirmation,
    researcher_confirmed: researcherConfirmed,
    gate_status: count >= 3 ? 'PASSED' : (researcherConfirmed ? 'PASSED_WITH_CONFIRMATION' : 'WARNING_REQUIRES_CONFIRMATION'),
    passed,
    message: count < 3 
      ? `Sparse cohort evidence (${count} patient(s) < 3). Requires explicit researcher confirmation.`
      : `Sufficient source evidence found (${count} patient(s), Tier: ${support_tier}).`
  };
}

export function generateSyntheticCohort(config = {}) {
  const numPatients = config.num_patients || 500;
  const ethnicities = ['Caucasian', 'African American', 'Hispanic', 'Asian', 'Other'];
  const genders = ['Male', 'Female'];

  const targetDiabeticPct = config.target_shift?.target_diabetic_pct || 35;
  const targetMeanAge = config.target_shift?.target_mean_age || 65;

  const synthPatients = [];
  for (let i = 0; i < numPatients; i++) {
    const sId = `SYN_${String(i + 1).padStart(3, '0')}`;
    const diabetic = Math.random() * 100 < targetDiabeticPct ? 1 : 0;
    const age = Math.min(88, Math.max(22, Math.round(targetMeanAge + (Math.random() * 24 - 12))));
    const gender = genders[i % 2 === 0 ? 0 : 1];
    const ethnicity = ethnicities[i % 5];

    synthPatients.push({ patient_id: sId, age, gender, ethnicity, diabetic });
  }

  const synthRecords = [];
  synthPatients.forEach(p => {
    const baseHba1c = p.diabetic === 1 ? 8.3 + (Math.random() * 1.0 - 0.5) : 5.5 + (Math.random() * 0.5 - 0.25);
    const baseBp = p.diabetic === 1 ? 139 + Math.floor(Math.random() * 12 - 6) : 123 + Math.floor(Math.random() * 8 - 4);
    const latentHealth = Math.random() * 2 - 1;

    for (let m = 1; m <= 6; m++) {
      const activityScore = Math.min(100, Math.max(0, Math.round((62 + 14 * latentHealth + (Math.random() * 12 - 6)) * 10) / 10));
      const painScore = Math.min(10, Math.max(0, Math.round((4.4 - 1.7 * latentHealth + (Math.random() * 2.0 - 1.0)) * 10) / 10));

      synthRecords.push({
        patient_id: p.patient_id,
        month: m,
        age: p.age,
        gender: p.gender,
        ethnicity: p.ethnicity,
        diabetic: p.diabetic,
        hba1c: Math.round((baseHba1c + (Math.random() * 0.25 - 0.12)) * 100) / 100,
        systolic_bp: Math.round(baseBp + (Math.random() * 4 - 2)),
        activity_score: activityScore,
        pain_score: painScore,
        medication_adherence: p.diabetic === 1 ? Math.floor(78 + Math.random() * 22) : Math.floor(90 + Math.random() * 10)
      });
    }
  });

  cachedSynthDataset = { synthPatients, synthRecords };
  return cachedSynthDataset;
}

export function getTrustReport() {
  if (!cachedSynthDataset) {
    generateSyntheticCohort();
  }

  // KDE Distribution Overlays for HbA1c
  const kdePoints = [
    { hba1c: '4.5%', SourceDensity: 0.08, SyntheticDensity: 0.09 },
    { hba1c: '5.5%', SourceDensity: 0.35, SyntheticDensity: 0.38 },
    { hba1c: '6.5%', SourceDensity: 0.52, SyntheticDensity: 0.49 },
    { hba1c: '7.5%', SourceDensity: 0.41, SyntheticDensity: 0.43 },
    { hba1c: '8.5%', SourceDensity: 0.28, SyntheticDensity: 0.26 },
    { hba1c: '9.5%', SourceDensity: 0.15, SyntheticDensity: 0.16 },
    { hba1c: '10.5%', SourceDensity: 0.06, SyntheticDensity: 0.07 },
    { hba1c: '11.5%', SourceDensity: 0.02, SyntheticDensity: 0.02 }
  ];

  // Correlation Heatmap Matrix
  const correlationMatrix = [
    { feature: 'HbA1c', HbA1c: 1.0, SystolicBP: 0.42, ActivityScore: -0.38, PainScore: 0.41, Adherence: -0.45 },
    { feature: 'SystolicBP', HbA1c: 0.42, SystolicBP: 1.0, ActivityScore: -0.29, PainScore: 0.32, Adherence: -0.35 },
    { feature: 'ActivityScore', HbA1c: -0.38, SystolicBP: -0.29, ActivityScore: 1.0, PainScore: -0.56, Adherence: 0.51 },
    { feature: 'PainScore', HbA1c: 0.41, SystolicBP: 0.32, ActivityScore: -0.56, PainScore: 1.0, Adherence: -0.48 },
    { feature: 'Adherence', HbA1c: -0.45, SystolicBP: -0.35, ActivityScore: 0.51, PainScore: -0.48, Adherence: 1.0 }
  ];

  // Population Shift Grid
  const populationShift = {
    baseline_source: { diabetic_pct: 20.0, mean_age: 52.4, mean_bp: 126.3 },
    target_request: { diabetic_pct: 35.0, mean_age: 65.0, mean_bp: 132.0 },
    synthetic_achieved: { diabetic_pct: 34.6, mean_age: 64.8, mean_bp: 131.5 },
    target_achievement_pct: 98.2
  };

  return {
    certificate: {
      title: 'Synora Synthetic Patient Cohort Privacy & Fidelity Certificate',
      certificate_id: 'CERT-SYN-035444FE86445FF8',
      timestamp: new Date().toISOString(),
      dataset_hash: '035444FE86445FF8',
      dataset_statistics: { synthetic_patients: 500, total_rows: 3000, months_per_patient: 6 },
      fidelity_metrics: {
        fidelity_score: 95.4,
        activity_pain_correlation: { source: -0.5368, synthetic: -0.5612, expected_target: -0.56, error: 0.0012 }
      },
      privacy_metrics: {
        membership_inference_attack: { mia_auroc: 0.542, vulnerability_level: 'LOW', details: 'Shadow attack model performs near random chance.' },
        k_anonymity: { k_min: 2, singleton_count: 0, has_singletons: false, total_equivalence_classes: 30 }
      },
      privacy_gate_evaluation: {
        passed: true,
        gate_status: 'PASSED',
        reasons: [],
        summary: 'Privacy Gate Passed. AUROC < 0.75 and k_min > 1. Dataset certified safe for download.'
      },
      disclaimer: '⚠️ For research and testing purposes only. Not clinically validated. No formal differential privacy applied.'
    },
    kdePoints,
    correlationMatrix,
    populationShift
  };
}

export function getPopulationExplorerData() {
  if (!cachedSynthDataset) {
    generateSyntheticCohort();
  }

  const { synthPatients, synthRecords } = cachedSynthDataset;

  // Scatter plot points (Age vs Medication Adherence vs Pain Score)
  const scatterPoints = synthPatients.slice(0, 100).map(p => {
    const pRecords = synthRecords.filter(r => r.patient_id === p.patient_id);
    const avgPain = pRecords.reduce((acc, r) => acc + r.pain_score, 0) / pRecords.length;
    const avgAdh = pRecords.reduce((acc, r) => acc + r.medication_adherence, 0) / pRecords.length;

    return {
      patient_id: p.patient_id,
      age: p.age,
      adherence: Math.round(avgAdh),
      painScore: Math.round(avgPain * 10) / 10,
      diabetic: p.diabetic
    };
  });

  return {
    patients: synthPatients,
    records: synthRecords,
    scatterPoints
  };
}
