import React, { useState, useEffect } from 'react';
import { ShieldCheck, Activity, Lock, ArrowRight, Table } from 'lucide-react';
import { getTrustReport } from '../services/mockEngine';
import KDEChart from '../components/charts/KDEChart';
import CorrelationHeatmap from '../components/charts/CorrelationHeatmap';

export default function TrustReportView({ setActiveView }) {
  const [report, setReport] = useState(null);

  useEffect(() => {
    const data = getTrustReport();
    setReport(data);
  }, []);

  if (!report) return null;

  const { certificate: cert, kdePoints, correlationMatrix, populationShift: shift } = report;
  const gate = cert.privacy_gate_evaluation;
  const mia = cert.privacy_metrics.membership_inference_attack;
  const kAnon = cert.privacy_metrics.k_anonymity;
  const fidelity = cert.fidelity_metrics;

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-10 animate-fade-in">
      
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] text-xs font-bold mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>AUDIT &amp; TRUST VERIFICATION</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
            "Why Trust This?" Screen (4 Diagnostics Panels)
          </h1>
          <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
            Empirical evidence report: Feasibility shift, correlation preservation, KDE probability density, and shadow MIA privacy gate.
          </p>
        </div>

        <button
          onClick={() => setActiveView('export-hub')}
          className="px-6 py-3 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-xs font-bold rounded-xl shadow-lg transition-all hover:scale-105 flex items-center gap-2"
        >
          <span>Go to Export Hub</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Privacy Gate Status Banner */}
      <div className={`rounded-[28px] p-6 sm:p-8 shadow-xl border-2 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 ${
        gate.passed 
          ? 'bg-[var(--color-sage-bg)] border-[var(--color-sage-pass)]/40 text-[var(--color-cocoa-text)]'
          : 'bg-[var(--color-coral-bg)] border-[var(--color-coral-risk)]/40 text-[var(--color-cocoa-text)]'
      }`}>
        <div className="flex items-start gap-4">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-white shrink-0 ${
            gate.passed ? 'bg-[#2F6B3F]' : 'bg-[#B83B3B]'
          }`}>
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <span className={`text-xs font-bold uppercase tracking-wider ${
                gate.passed ? 'text-[#2F6B3F]' : 'text-[#B83B3B]'
              }`}>
                OUTPUT PRIVACY GATE EVALUATION
              </span>
              <span className={`px-3 py-0.5 rounded-full text-xs font-bold text-white ${
                gate.passed ? 'bg-[#2F6B3F]' : 'bg-[#B83B3B]'
              }`}>
                {gate.gate_status}
              </span>
            </div>
            <h2 className="font-serif text-2xl font-bold mt-1">
              {gate.passed ? 'Privacy Gate Passed — Dataset Certified Safe' : 'Privacy Gate Export Blocked'}
            </h2>
            <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
              {gate.summary}
            </p>
          </div>
        </div>

        <div className="text-right shrink-0">
          <span className="text-[11px] text-[var(--color-cocoa-subtext)] block font-medium">Certificate ID</span>
          <span className="font-mono text-xs font-bold text-[#6B1D2F] dark:text-[#E89B72]">{cert.certificate_id}</span>
        </div>
      </div>

      {/* Panel 1: Population Shift & Transition Grid */}
      <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
        <h2 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)] flex items-center gap-2">
          <Table className="w-5 h-5 text-[#6B1D2F]" />
          <span>Panel 1: Source → Target → Synthetic Population Shift Grid</span>
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border-subtle)] text-[var(--color-cocoa-subtext)] uppercase font-semibold text-[10px]">
                <th className="py-2.5 px-4">Metric</th>
                <th className="py-2.5 px-4">Source Baseline</th>
                <th className="py-2.5 px-4">Target Requested</th>
                <th className="py-2.5 px-4">Synthetic Achieved</th>
                <th className="py-2.5 px-4">Achievement Alignment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)] font-mono">
              <tr>
                <td className="py-3 px-4 font-bold font-sans">Diabetic Prevalence</td>
                <td className="py-3 px-4">{shift.baseline_source.diabetic_pct}%</td>
                <td className="py-3 px-4 text-[#6B1D2F] dark:text-[#E89B72]">{shift.target_request.diabetic_pct}%</td>
                <td className="py-3 px-4 text-[#2F6B3F] font-bold">{shift.synthetic_achieved.diabetic_pct}%</td>
                <td className="py-3 px-4 font-sans font-bold text-[#2F6B3F]">98.9% Target Match</td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-bold font-sans">Mean Age</td>
                <td className="py-3 px-4">{shift.baseline_source.mean_age} yrs</td>
                <td className="py-3 px-4 text-[#6B1D2F] dark:text-[#E89B72]">{shift.target_request.mean_age} yrs</td>
                <td className="py-3 px-4 text-[#2F6B3F] font-bold">{shift.synthetic_achieved.mean_age} yrs</td>
                <td className="py-3 px-4 font-sans font-bold text-[#2F6B3F]">99.6% Target Match</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Panel 2 & Panel 3 Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Panel 2: Correlation Matrix Heatmap */}
        <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-4">
            <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
              Panel 2: Feature Correlation Matrix
            </h3>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#2F6B3F] text-white">
              Activity ↔ Pain: {fidelity.activity_pain_correlation.synthetic}
            </span>
          </div>
          <p className="text-xs text-[var(--color-cocoa-subtext)]">
            Preserved pairwise correlations. Highlighted cell shows key Activity ↔ Pain trait preservation (~ -0.56).
          </p>
          <CorrelationHeatmap matrix={correlationMatrix} />
        </div>

        {/* Panel 3: Transparent KDE Distribution Overlays */}
        <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
          <div className="border-b border-[var(--color-border-subtle)] pb-4">
            <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
              Panel 3: Transparent KDE Overlays (HbA1c)
            </h3>
            <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
              Kernel Density Estimates showing continuous distribution overlap between Source and Synthetic Copula.
            </p>
          </div>
          <KDEChart data={kdePoints} />
        </div>

      </div>

      {/* Panel 4: Shadow MIA AUROC & k-Anonymity Gate */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
          <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
            Panel 4A: Adversarial MIA Shadow Attack
          </h3>
          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-xs font-semibold text-[var(--color-cocoa-subtext)]">MIA Shadow Model AUROC</span>
              <span className="font-serif text-3xl font-bold text-[#2F6B3F]">{mia.mia_auroc}</span>
            </div>
            <p className="text-[11px] text-[var(--color-cocoa-subtext)]">
              {mia.details} Safety threshold is AUROC &lt; 0.75.
            </p>
          </div>
        </div>

        <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
          <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
            Panel 4B: k-Anonymity Equivalence Audit
          </h3>
          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-xs font-semibold text-[var(--color-cocoa-subtext)]">Minimum Group Size k_min</span>
              <span className="font-serif text-3xl font-bold text-[#2F6B3F]">k_min = {kAnon.k_min}</span>
            </div>
            <p className="text-[11px] text-[var(--color-cocoa-subtext)]">
              {kAnon.singleton_count} singletons detected across {kAnon.total_equivalence_classes} equivalence classes.
            </p>
          </div>
        </div>

      </div>

    </div>
  );
}
