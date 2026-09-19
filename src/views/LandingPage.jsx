import React from 'react';
import CohortDNA from '../components/CohortDNA';
import { ArrowRight, ShieldCheck, Database, Sliders, Dna, Activity, Lock, Cpu, CheckCircle2, AlertTriangle, Play } from 'lucide-react';

export default function LandingPage({ setActiveView, openAuthModal }) {
  return (
    <div className="space-y-24 py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      
      {/* HERO SECTION with Spiral Entry Animation */}
      <section className="relative text-center space-y-8 animate-spiral-zoom pt-8">
        
        {/* Glowing Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#6B1D2F]/10 border border-[#6B1D2F]/20 text-[#6B1D2F] dark:text-[#E89B72] text-xs font-bold tracking-wide">
          <Dna className="w-4 h-4 animate-spin" style={{ animationDuration: '10s' }} />
          <span>RESEARCHER-FIRST DECISION LAYER</span>
        </div>

        {/* Hero Title */}
        <h1 className="font-serif text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-[var(--color-cocoa-text)] max-w-4xl mx-auto leading-[1.1]">
          Synthetic Cohort Generation with <span className="text-[#6B1D2F] dark:text-[#E89B72] underline decoration-wavy decoration-1 underline-offset-8">Symmetric Privacy Gates</span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-base sm:text-xl text-[var(--color-cocoa-subtext)] max-w-2xl mx-auto font-normal leading-relaxed">
          Checks ground-truth evidence <em>before</em> generation and executes shadow membership attacks <em>after</em> generation. Zero guesswork, certified safety.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
          <button
            onClick={() => setActiveView('cohort-designer')}
            className="px-8 py-4 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-sm font-bold rounded-2xl shadow-xl hover:shadow-2xl transition-all hover:scale-105 flex items-center gap-3 group"
          >
            <span>Launch Cohort Designer</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>

          <button
            onClick={() => setActiveView('dataset-dna')}
            className="px-7 py-4 border-2 border-[var(--color-border-subtle)] bg-[var(--color-card-white)] hover:bg-[var(--color-cream-surface)] text-[var(--color-cocoa-text)] text-sm font-bold rounded-2xl transition-all flex items-center gap-2"
          >
            <Database className="w-4 h-4 text-[#6B1D2F] dark:text-[#E89B72]" />
            <span>Explore Dataset DNA</span>
          </button>
        </div>

        {/* Interactive 3D Cohort DNA */}
        <div className="pt-8 max-w-5xl mx-auto">
          <div className="rounded-[32px] bg-[var(--color-card-white)] border border-[var(--color-border-subtle)] shadow-2xl overflow-hidden glow-terracotta">
            <div className="px-6 sm:px-8 pt-7 text-center">
              <p className="text-[10px] font-bold tracking-[0.2em] text-[#6B1D2F] dark:text-[#E89B72]">
                SOURCE POPULATION INTELLIGENCE
              </p>
              <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[var(--color-cocoa-text)] mt-2">
                Explore your Cohort DNA
              </h2>
              <p className="text-xs sm:text-sm text-[var(--color-cocoa-subtext)] max-w-xl mx-auto mt-2">
                Six clinical dimensions form the foundation of Synora's cohort intelligence.
                Click the 3D model to inspect the dataset behind your synthetic cohorts.
              </p>
            </div>

            <CohortDNA setActiveView={setActiveView} />
          </div>
        </div>

      </section>

      {/* DUAL SYMMETRIC GATES ARCHITECTURE SECTION */}
      <section className="space-y-12">
        <div className="text-center space-y-3">
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
            The Two Symmetric Gates Architecture
          </h2>
          <p className="text-sm text-[var(--color-cocoa-subtext)] max-w-2xl mx-auto">
            Synora enforces rigorous mathematical checks on both sides of synthetic generation to eliminate hallucinations and data leakage.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Gate 1: Feasibility Gate */}
          <div className="rounded-[24px] bg-[var(--color-card-white)] p-8 shadow-xl border-2 border-[var(--color-border-subtle)] hover:border-[#6B1D2F]/40 transition-all space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-[#C68B2C]/10 text-[#C68B2C] flex items-center justify-center">
              <Sliders className="w-6 h-6" />
            </div>
            <span className="inline-block text-xs font-bold uppercase tracking-wider text-[#C68B2C]">
              INPUT SIDE GATE
            </span>
            <h3 className="font-serif text-2xl font-bold text-[var(--color-cocoa-text)]">
              1. Feasibility Gate
            </h3>
            <p className="text-xs leading-relaxed text-[var(--color-cocoa-subtext)]">
              Before fitting generative copula models, Synora checks source patient evidence count. Subgroup queries with fewer than 3 source patients trigger a mandatory <strong>Researcher Confirmation Lock</strong> to prevent overfitting on sparse noise.
            </p>
            <div className="p-4 rounded-xl bg-[var(--color-cream-surface)] text-xs font-mono space-y-1">
              <div className="text-[var(--color-cocoa-text)] font-semibold">Support Tiers:</div>
              <div className="text-[#2F6B3F]">✓ Strong: ≥ 30 Patients</div>
              <div className="text-[#C68B2C]">⚡ Moderate: 10–29 Patients</div>
              <div className="text-[#B83B3B]">⚠️ Sparse: 3–9 Patients</div>
              <div className="text-[#B83B3B] font-bold">⛔ Unsupported: &lt; 3 (Requires Override)</div>
            </div>
          </div>

          {/* Gate 2: Privacy Gate */}
          <div className="rounded-[24px] bg-[var(--color-card-white)] p-8 shadow-xl border-2 border-[var(--color-border-subtle)] hover:border-[#6B1D2F]/40 transition-all space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] flex items-center justify-center">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <span className="inline-block text-xs font-bold uppercase tracking-wider text-[#6B1D2F] dark:text-[#E89B72]">
              OUTPUT SIDE GATE
            </span>
            <h3 className="font-serif text-2xl font-bold text-[var(--color-cocoa-text)]">
              2. Privacy Gate
            </h3>
            <p className="text-xs leading-relaxed text-[var(--color-cocoa-subtext)]">
              After generation, Synora runs an adversarial <strong>Membership Inference Attack (MIA)</strong> shadow model and checks <strong>k-anonymity</strong> equivalence classes. Downloads are automatically <strong>BLOCKED</strong> if MIA AUROC ≥ 0.75 or minimum group size k_min = 1.
            </p>
            <div className="p-4 rounded-xl bg-[var(--color-cream-surface)] text-xs font-mono space-y-1">
              <div className="text-[var(--color-cocoa-text)] font-semibold">Privacy Thresholds:</div>
              <div className="text-[#2F6B3F]">✓ Safe MIA Score: AUROC &lt; 0.75 (Target: 0.48–0.60)</div>
              <div className="text-[#2F6B3F]">✓ k-Anonymity: k_min &gt; 1 (No singletons)</div>
              <div className="text-[#6B1D2F] font-bold">📜 Auto-Issued: privacy_certificate.json</div>
            </div>
          </div>

        </div>
      </section>

      {/* CALL TO ACTION BOTTOM BANNER */}
      <section className="rounded-[32px] bg-gradient-to-r from-[#6B1D2F] to-[#8B263E] p-8 sm:p-12 text-white text-center space-y-6 shadow-2xl relative overflow-hidden">
        <h2 className="font-serif text-3xl sm:text-5xl font-bold max-w-2xl mx-auto">
          Ready to Build Evidence-Based Patient Cohorts?
        </h2>
        <p className="text-sm opacity-90 max-w-xl mx-auto">
          Join leading clinical researchers generating safe, high-fidelity synthetic data with complete privacy certificates.
        </p>
        <div className="pt-2">
          <button
            onClick={() => setActiveView('cohort-designer')}
            className="px-8 py-4 bg-white text-[#6B1D2F] hover:bg-[var(--color-cream-canvas)] text-sm font-bold rounded-2xl shadow-lg transition-all hover:scale-105 inline-flex items-center gap-2"
          >
            <span>Start Building Cohort</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

    </div>
  );
}
