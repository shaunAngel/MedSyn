import React from 'react';
import { X, ShieldCheck, FileText } from 'lucide-react';

export default function PrivacyTermsModals({ activeModal, onClose }) {
  if (!activeModal) return null;

  const isPrivacy = activeModal === 'privacy';

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div className="relative w-full max-w-2xl bg-[var(--color-card-white)] rounded-[24px] p-6 sm:p-8 shadow-2xl border border-[var(--color-border-subtle)] text-[var(--color-cocoa-text)] max-h-[85vh] overflow-y-auto">
        
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full hover:bg-[var(--color-cream-surface)] text-[var(--color-cocoa-subtext)] transition-colors"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-[#6B1D2F] text-white">
            {isPrivacy ? <ShieldCheck className="w-6 h-6" /> : <FileText className="w-6 h-6" />}
          </div>
          <div>
            <h2 className="font-serif text-2xl font-bold">
              {isPrivacy ? 'Privacy Policy & Governance' : 'Terms of Service & Research License'}
            </h2>
            <p className="text-xs text-[var(--color-cocoa-subtext)]">Effective Date: September 2026</p>
          </div>
        </div>

        <div className="space-y-4 text-xs leading-relaxed text-[var(--color-cocoa-subtext)] border-t border-[var(--color-border-subtle)] pt-4">
          {isPrivacy ? (
            <>
              <h3 className="font-bold text-[var(--color-cocoa-text)] text-sm">1. Ground-Truth Data Isolation</h3>
              <p>
                Synora operates on a zero-egress principle for raw source datasets. Source evidence is processed locally to compute schema and subgroup frequencies. Raw patient identifiers are never exported or combined into model artifacts.
              </p>

              <h3 className="font-bold text-[var(--color-cocoa-text)] text-sm">2. Membership Inference & k-Anonymity Auditing</h3>
              <p>
                Post-generation synthetic data undergoes automated shadow model Membership Inference Attacks (MIA) and k-anonymity equivalence class checks before release. Datasets triggering MIA AUROC ≥ 0.75 or k_min = 1 (singletons) are automatically blocked by the Privacy Gate.
              </p>

              <h3 className="font-bold text-[var(--color-cocoa-text)] text-sm">3. Session & Local Data Retention</h3>
              <p>
                No Protected Health Information (PHI) is transmitted or stored on public cloud servers. All cohort generation tasks run in memory within your secured execution workspace.
              </p>
            </>
          ) : (
            <>
              <h3 className="font-bold text-[var(--color-cocoa-text)] text-sm">1. Mandatory Research Disclaimer</h3>
              <p className="bg-[var(--color-coral-bg)] p-3 rounded-xl text-[var(--color-coral-risk)] font-medium border border-[var(--color-coral-risk)]/20">
                ⚠️ Synora is strictly intended for scientific research, methodology benchmarking, and software testing. It is not clinically validated for direct patient care, diagnostics, or therapeutic interventions. No formal differential privacy ($\epsilon$-DP) guarantees are implied unless explicitly configured.
              </p>

              <h3 className="font-bold text-[var(--color-cocoa-text)] text-sm">2. Symmetric Gates Compliance</h3>
              <p>
                Researchers agree not to attempt reverse-engineering or circumventing Feasibility Gate warning locks or output Privacy Gate export blocks. Attempting re-identification attacks on external subjects using generated datasets is strictly prohibited.
              </p>

              <h3 className="font-bold text-[var(--color-cocoa-text)] text-sm">3. License & Attribution</h3>
              <p>
                Synthetic datasets generated with valid Privacy Certificates carry open research rights. Citation of Synora's dual-gate decision architecture is requested in published literature.
              </p>
            </>
          )}
        </div>

        <div className="mt-6 pt-4 border-t border-[var(--color-border-subtle)] flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-xs font-bold rounded-xl shadow-md transition-all"
          >
            I Understand & Agree
          </button>
        </div>
      </div>
    </div>
  );
}
