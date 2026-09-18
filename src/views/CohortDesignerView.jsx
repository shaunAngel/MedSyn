import React, { useState, useEffect } from 'react';
import { Sliders, ShieldCheck, AlertTriangle, Play, RefreshCw, CheckCircle2, Lock } from 'lucide-react';
import { evaluateFeasibility } from '../services/api';

export default function CohortDesignerView({ onStartGeneration }) {
  const [filters, setFilters] = useState({
    diabetic: 1,
    age_min: 66,
    age_max: 90,
    gender: 'All',
    ethnicity: 'Other' // Triggers sparse benchmark count = 2 patients!
  });

  const [targetShift, setTargetShift] = useState({
    target_diabetic_pct: 35,
    target_mean_age: 68
  });

  const [researcherConfirmed, setResearcherConfirmed] = useState(false);
  const [feasibility, setFeasibility] = useState(null);

  // Real-time Feasibility Gate assessment on filter changes
  useEffect(() => {
    const res = evaluateFeasibility(filters, researcherConfirmed);
    setFeasibility(res);
  }, [filters, researcherConfirmed]);

  const handleRun = () => {
    if (!feasibility || !feasibility.passed) return;
    onStartGeneration({
      filters,
      targetShift,
      researcherConfirmed
    });
  };

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8 animate-fade-in">
      
      {/* Header */}
      <div className="border-b border-[var(--color-border-subtle)] pb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] text-xs font-bold mb-2">
          <Sliders className="w-3.5 h-3.5" />
          <span>INPUT FEASIBILITY GATE ENGINE</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
          Cohort Designer &amp; Feasibility Gate
        </h1>
        <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
          Specify target subgroup parameters. The Feasibility Gate checks source evidence before fitting generative copula models.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Filter Controls & Fast Forms Inputs */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Subgroup Filters Card */}
          <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-6">
            <h2 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
              1. Target Subgroup Criteria
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* Diabetic Status */}
              <div>
                <label className="block text-xs font-semibold mb-1">Diabetic Condition</label>
                <select
                  value={filters.diabetic}
                  onChange={(e) => setFilters({ ...filters, diabetic: e.target.value })}
                  className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F]"
                >
                  <option value="1">Diabetic Patients Only (diabetic = 1)</option>
                  <option value="0">Non-Diabetic Patients (diabetic = 0)</option>
                  <option value="All">All Patients (Combined)</option>
                </select>
              </div>

              {/* Ethnicity */}
              <div>
                <label className="block text-xs font-semibold mb-1">Ethnicity Subgroup</label>
                <select
                  value={filters.ethnicity}
                  onChange={(e) => setFilters({ ...filters, ethnicity: e.target.value })}
                  className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F]"
                >
                  <option value="Other">Other (Sparse Subgroup Demo - 2 Patients)</option>
                  <option value="Caucasian">Caucasian</option>
                  <option value="African American">African American</option>
                  <option value="Hispanic">Hispanic</option>
                  <option value="Asian">Asian</option>
                  <option value="All">All Ethnicities</option>
                </select>
              </div>

              {/* Age Range Slider / Inputs */}
              <div>
                <label className="block text-xs font-semibold mb-1">
                  Age Range: <span className="text-[#6B1D2F] dark:text-[#E89B72]">{filters.age_min} to {filters.age_max} years</span>
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="18"
                    max="90"
                    value={filters.age_min}
                    onChange={(e) => setFilters({ ...filters, age_min: e.target.value })}
                    className="w-full accent-[#6B1D2F]"
                  />
                </div>
              </div>

              {/* Gender */}
              <div>
                <label className="block text-xs font-semibold mb-1">Gender Filter</label>
                <select
                  value={filters.gender}
                  onChange={(e) => setFilters({ ...filters, gender: e.target.value })}
                  className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F]"
                >
                  <option value="All">All Genders</option>
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                </select>
              </div>

            </div>
          </div>

          {/* Population Shift Sliders Card */}
          <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-6">
            <h2 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
              2. Target Population Shift Specification
            </h2>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span>Target Diabetic Prevalence</span>
                  <span className="text-[#6B1D2F] dark:text-[#E89B72]">{targetShift.target_diabetic_pct}% (Baseline: 20.0%)</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="60"
                  value={targetShift.target_diabetic_pct}
                  onChange={(e) => setTargetShift({ ...targetShift, target_diabetic_pct: Number(e.target.value) })}
                  className="w-full accent-[#6B1D2F]"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span>Target Mean Age</span>
                  <span className="text-[#6B1D2F] dark:text-[#E89B72]">{targetShift.target_mean_age} years (Baseline: 52.4 yrs)</span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="80"
                  value={targetShift.target_mean_age}
                  onChange={(e) => setTargetShift({ ...targetShift, target_mean_age: Number(e.target.value) })}
                  className="w-full accent-[#6B1D2F]"
                />
              </div>
            </div>
          </div>

        </div>

        {/* Right Column: Real-Time Feasibility Gate Status Banner */}
        <div className="space-y-6">
          
          <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 shadow-xl border-2 border-[var(--color-border-subtle)] space-y-6 sticky top-24">
            <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-4">
              <h3 className="font-serif font-bold text-lg text-[var(--color-cocoa-text)] flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-[#6B1D2F]" />
                <span>Feasibility Gate Status</span>
              </h3>
            </div>

            {feasibility && (
              <div className="space-y-4">
                
                {/* Count & Tier Badge */}
                <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] border border-[var(--color-border-subtle)] flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-[var(--color-cocoa-subtext)] block font-medium">Source Evidence Count</span>
                    <span className="font-serif text-3xl font-bold text-[#6B1D2F] dark:text-[#E89B72]">
                      {feasibility.matching_patient_count} Patients
                    </span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                    feasibility.support_tier === 'Strong' 
                      ? 'bg-[#2F6B3F] text-white' 
                      : (feasibility.support_tier === 'Moderate' ? 'bg-[#C68B2C] text-white' : 'bg-[#B83B3B] text-white')
                  }`}>
                    {feasibility.support_tier} Support
                  </span>
                </div>

                {/* Warning Alert if Sparse (< 3 patients) */}
                {feasibility.requires_confirmation && (
                  <div className="p-4 rounded-2xl bg-[var(--color-coral-bg)] border border-[var(--color-coral-risk)]/40 space-y-3">
                    <div className="flex items-start gap-2 text-[#B83B3B]">
                      <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider">Sparse Evidence Warning</h4>
                        <p className="text-[11px] leading-relaxed mt-1">
                          Source count ({feasibility.matching_patient_count} patient(s)) is &lt; 3. Generating from sparse data risks model overfitting and memoization.
                        </p>
                      </div>
                    </div>

                    {/* Researcher Confirmation Override Toggle */}
                    <label className="flex items-center gap-3 p-3 rounded-xl bg-white/80 dark:bg-black/30 border border-[#B83B3B]/30 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={researcherConfirmed}
                        onChange={(e) => setResearcherConfirmed(e.target.checked)}
                        className="w-4 h-4 rounded text-[#6B1D2F] focus:ring-[#6B1D2F]"
                      />
                      <span className="text-[11px] font-bold text-[var(--color-cocoa-text)]">
                        Researcher Explicit Confirmation Override
                      </span>
                    </label>
                  </div>
                )}

                {/* Gate Pass / Lock Banner */}
                <div className={`p-4 rounded-2xl text-xs font-semibold flex items-center gap-2 ${
                  feasibility.passed 
                    ? 'bg-[#EAF4EC] text-[#2F6B3F] border border-[#2F6B3F]/30' 
                    : 'bg-[#FDECEC] text-[#B83B3B] border border-[#B83B3B]/30'
                }`}>
                  {feasibility.passed ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <Lock className="w-5 h-5 shrink-0" />}
                  <span>{feasibility.message}</span>
                </div>

                {/* Launch Generation Button */}
                <button
                  onClick={handleRun}
                  disabled={!feasibility.passed}
                  className={`w-full py-4 text-xs font-bold rounded-2xl shadow-xl transition-all flex items-center justify-center gap-2 ${
                    feasibility.passed
                      ? 'bg-[#6B1D2F] hover:bg-[#8B263E] text-white hover:scale-[1.02]'
                      : 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  <Play className="w-4 h-4 fill-current" />
                  <span>Generate 500 Synthetic Trajectories</span>
                </button>

              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
