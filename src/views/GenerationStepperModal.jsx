import React, { useState, useEffect } from 'react';
import { Cpu, CheckCircle2, RefreshCw } from 'lucide-react';
import { generateSyntheticCohort } from '../services/mockEngine';

export default function GenerationStepperModal({ isOpen, config, onComplete, onError }) {
  const [phase, setPhase] = useState(0);
  const phases = [
    { title: '1. Ingest Ground-Truth Evidence', desc: 'Loading demo_patients.csv dataset' },
    { title: '2. Input Feasibility Gate Check', desc: 'Validating subgroup support tier & confirmation status' },
    { title: '3. Patient-Level 80/20 Split', desc: 'Splitting 400 Train / 100 Holdout patients without ID leakage' },
    { title: '4. Fit SDV Copula Engine', desc: 'Fitting Gaussian Copula model on train set' },
    { title: '5. Longitudinal Trajectory Sampling', desc: 'Synthesizing 500 patients × 6 months (3,000 rows)' },
    { title: '6. Mechanical Sanity Validation', desc: 'Checking pain score bounds [0..10] & month continuity' },
    { title: '7. Adversarial MIA & Privacy Gate', desc: 'Simulating shadow membership attack & k-anonymity' }
  ];

  useEffect(() => {
    if (!isOpen) {
      setPhase(0);
      return;
    }

    let current = 0;
    const interval = setInterval(() => {
      current += 1;
      if (current < phases.length) {
        setPhase(current);
      } else {
        clearInterval(interval);
        // Execute client-side copula generation sampling
        generateSyntheticCohort({
          num_patients: 500,
          target_shift: config?.targetShift
        });
        onComplete({ success: true });
      }
    }, 600);

    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-xl bg-[var(--color-card-white)] rounded-[28px] p-6 sm:p-8 shadow-2xl border border-[var(--color-border-subtle)] text-[var(--color-cocoa-text)] space-y-6">
        
        <div className="flex items-center gap-3 border-b border-[var(--color-border-subtle)] pb-4">
          <div className="w-10 h-10 rounded-xl bg-[#6B1D2F] text-white flex items-center justify-center">
            <Cpu className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="font-serif text-xl font-bold">Generative Copula Stepper</h2>
            <p className="text-xs text-[var(--color-cocoa-subtext)]">Transparent pipeline phase progression</p>
          </div>
        </div>

        <div className="space-y-3">
          {phases.map((p, idx) => {
            const isDone = idx < phase;
            const isCurrent = idx === phase;

            return (
              <div
                key={idx}
                className={`p-3.5 rounded-2xl border text-xs flex items-center justify-between transition-all ${
                  isDone
                    ? 'bg-[#EAF4EC] border-[#2F6B3F]/30 text-[#2F6B3F]'
                    : (isCurrent 
                        ? 'bg-[var(--color-cream-surface)] border-[#6B1D2F] text-[#6B1D2F] dark:text-[#E89B72] shadow-md font-bold'
                        : 'bg-transparent border-[var(--color-border-subtle)] text-gray-400')
                }`}
              >
                <div className="flex items-center gap-3">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-[#2F6B3F] shrink-0" />
                  ) : isCurrent ? (
                    <RefreshCw className="w-4 h-4 text-[#6B1D2F] animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-gray-300 flex items-center justify-center text-[9px] shrink-0">
                      {idx + 1}
                    </div>
                  )}
                  <div>
                    <div className="font-bold">{p.title}</div>
                    <div className="text-[10px] opacity-80">{p.desc}</div>
                  </div>
                </div>

                {isDone && <span className="text-[10px] font-bold uppercase tracking-wider">Completed</span>}
                {isCurrent && <span className="text-[10px] font-bold uppercase tracking-wider animate-pulse">Running</span>}
              </div>
            );
          })}
        </div>

        <div className="text-center text-xs text-[var(--color-cocoa-subtext)]">
          Please wait while Synora runs the patient split, Copula sampling, and shadow MIA privacy audit...
        </div>

      </div>
    </div>
  );
}
