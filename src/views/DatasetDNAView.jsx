import React, { useState, useEffect } from 'react';
import { Database, Activity, AlertTriangle, ArrowRight, BarChart2 } from 'lucide-react';
import { getDatasetDNA } from '../services/mockEngine';
import DemographicsChart from '../components/charts/DemographicsChart';

export default function DatasetDNAView({ setActiveView }) {
  const [dnaData, setDnaData] = useState(null);

  useEffect(() => {
    const data = getDatasetDNA();
    setDnaData(data);
  }, []);

  if (!dnaData) return null;

  const { schema, benchmarks, sparsity_health, demographics } = dnaData;

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-10 animate-fade-in">
      
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] text-xs font-bold mb-2">
            <Database className="w-3.5 h-3.5" />
            <span>GROUND-TRUTH EVIDENCE LAYER</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
            Dataset DNA Intelligence
          </h1>
          <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
            Structural audit of demo_patients.csv source evidence prior to synthetic generation.
          </p>
        </div>

        <button
          onClick={() => setActiveView('cohort-designer')}
          className="px-6 py-3 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-xs font-bold rounded-xl shadow-lg transition-all hover:scale-105 flex items-center gap-2"
        >
          <span>Design Cohort</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Core Ground-Truth Metadata Card */}
      <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-6">
        <h2 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)] flex items-center gap-2">
          <Activity className="w-5 h-5 text-[#6B1D2F]" />
          <span>Core Ground-Truth Metadata</span>
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] border border-[var(--color-border-subtle)]">
            <span className="text-[11px] font-semibold text-[var(--color-cocoa-subtext)]">Total Patients</span>
            <span className="block font-serif text-3xl font-bold text-[#6B1D2F] dark:text-[#E89B72] mt-1">{schema.total_patients}</span>
            <span className="text-[10px] text-gray-500">Unique IDs (P001..P500)</span>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] border border-[var(--color-border-subtle)]">
            <span className="text-[11px] font-semibold text-[var(--color-cocoa-subtext)]">Longitudinal Rows</span>
            <span className="block font-serif text-3xl font-bold text-[#6B1D2F] dark:text-[#E89B72] mt-1">{schema.total_rows}</span>
            <span className="text-[10px] text-gray-500">6 Months per Patient</span>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] border border-[var(--color-border-subtle)]">
            <span className="text-[11px] font-semibold text-[var(--color-cocoa-subtext)]">Activity ↔ Pain Correlation</span>
            <span className="block font-serif text-3xl font-bold text-[#2F6B3F] mt-1">-0.56</span>
            <span className="text-[10px] text-gray-500">Preserved Latent Trait</span>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] border border-[var(--color-border-subtle)]">
            <span className="text-[11px] font-semibold text-[var(--color-cocoa-subtext)]">Sparsity Health Index</span>
            <span className="block font-serif text-3xl font-bold text-[#C68B2C] mt-1">{sparsity_health.health_score}%</span>
            <span className="text-[10px] text-gray-500">Coverage Score</span>
          </div>
        </div>
      </div>

      {/* Demographics Bar & Doughnut Visualizations */}
      <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-6">
        <h2 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)] flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-[#6B1D2F]" />
          <span>Demographic Distribution Visualizations</span>
        </h2>

        <DemographicsChart 
          ageData={demographics.ageHistogram} 
          genderData={demographics.genderDoughnut} 
        />
      </div>

      {/* Sparsity Health Benchmarks Matrix */}
      <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-6">
        <div>
          <h2 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)] flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-[#C68B2C]" />
            <span>Key Subgroup Evidence Benchmarks</span>
          </h2>
          <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
            Ground-truth patient counts across single, double, and triple dimensional combinations.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-5 rounded-2xl bg-[var(--color-sage-bg)] border border-[var(--color-sage-pass)]/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#2F6B3F]">Diabetic Subgroup</span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#2F6B3F] text-white">STRONG TIER</span>
            </div>
            <div className="font-serif text-3xl font-bold text-[#2F6B3F]">{benchmarks.diabetic_count} Patients</div>
            <p className="text-[11px] text-[var(--color-cocoa-subtext)]">20.0% of source population. Robust evidence support.</p>
          </div>

          <div className="p-5 rounded-2xl bg-[var(--color-amber-bg)] border border-[var(--color-amber-caution)]/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#C68B2C]">Diabetic + Age &gt; 65</span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#C68B2C] text-white">MODERATE TIER</span>
            </div>
            <div className="font-serif text-3xl font-bold text-[#C68B2C]">{benchmarks.diabetic_age_gt_65} Patients</div>
            <p className="text-[11px] text-[var(--color-cocoa-subtext)]">5.0% of source population. Moderate copula support.</p>
          </div>

          <div className="p-5 rounded-2xl bg-[var(--color-coral-bg)] border border-[var(--color-coral-risk)]/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#B83B3B]">Diabetic + Age &gt; 65 + 'Other'</span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#B83B3B] text-white">SPARSE TIER (&lt; 3)</span>
            </div>
            <div className="font-serif text-3xl font-bold text-[#B83B3B]">{benchmarks.triple_combo_sparse} Patients</div>
            <p className="text-[11px] text-[#B83B3B] font-semibold">⚠️ Triggers Feasibility Gate Confirmation Lock on input.</p>
          </div>
        </div>
      </div>

      {/* Schema Detector Table */}
      <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-6">
        <h2 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
          Auto-Detected Feature Schema
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border-subtle)] text-[var(--color-cocoa-subtext)] uppercase font-semibold text-[10px] tracking-wider">
                <th className="py-3 px-4">Feature Name</th>
                <th className="py-3 px-4">Data Type</th>
                <th className="py-3 px-4">Category / Range</th>
                <th className="py-3 px-4">Mean Value</th>
                <th className="py-3 px-4">Copula Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)] font-mono">
              {Object.entries(schema.columns).map(([col, details]) => (
                <tr key={col} className="hover:bg-[var(--color-cream-surface)] transition-colors">
                  <td className="py-3.5 px-4 font-bold font-sans text-[var(--color-cocoa-text)]">{col}</td>
                  <td className="py-3.5 px-4 text-gray-500">{details.dtype}</td>
                  <td className="py-3.5 px-4">
                    {details.type === 'categorical'
                      ? (details.categories ? details.categories.join(', ') : 'Categorical')
                      : `[${details.min} .. ${details.max}]`}
                  </td>
                  <td className="py-3.5 px-4 text-[#6B1D2F] dark:text-[#E89B72]">
                    {details.mean !== null ? details.mean : 'N/A'}
                  </td>
                  <td className="py-3.5 px-4 font-sans text-[11px]">
                    {['age', 'gender', 'ethnicity', 'diabetic'].includes(col) ? (
                      <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">Quasi-Identifier</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-semibold">Longitudinal Signal</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
