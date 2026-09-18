import React from 'react';
import { Dna, ShieldCheck, FileText, HelpCircle, ExternalLink } from 'lucide-react';

export default function Footer({ openModal, setActiveView }) {
  return (
    <footer className="bg-[var(--color-cream-surface)] border-t border-[var(--color-border-subtle)] py-12 px-4 sm:px-6 lg:px-8 mt-20 transition-colors">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
        
        {/* Brand column */}
        <div className="md:col-span-2 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#6B1D2F] text-white flex items-center justify-center font-bold">
              <Dna className="w-5 h-5" />
            </div>
            <span className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">Synora</span>
          </div>
          <p className="text-xs text-[var(--color-cocoa-subtext)] max-w-sm leading-relaxed">
            Synora is the researcher-first decision layer that checks ground-truth source evidence before synthetic generation and executes adversarial privacy attacks post-generation.
          </p>
          <div className="text-[11px] text-[var(--color-cocoa-subtext)]">
            Ground-Truth Baseline: 500 Patients × 6 Months (3,000 longitudinal records).
          </div>
        </div>

        {/* Quick Links */}
        <div>
          <h4 className="font-serif font-bold text-xs uppercase tracking-wider text-[var(--color-cocoa-text)] mb-3">
            Platform Views
          </h4>
          <ul className="space-y-2 text-xs">
            <li>
              <button onClick={() => setActiveView('dataset-dna')} className="text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                Dataset DNA Intelligence
              </button>
            </li>
            <li>
              <button onClick={() => setActiveView('cohort-designer')} className="text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                Cohort Designer & Feasibility Gate
              </button>
            </li>
            <li>
              <button onClick={() => setActiveView('trust-report')} className="text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                Why Trust This? Validation
              </button>
            </li>
            <li>
              <button onClick={() => setActiveView('explorer')} className="text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                Population Explorer
              </button>
            </li>
            <li>
              <button onClick={() => setActiveView('export-hub')} className="text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                Export Hub & Certificate
              </button>
            </li>
          </ul>
        </div>

        {/* Legal & Governance */}
        <div>
          <h4 className="font-serif font-bold text-xs uppercase tracking-wider text-[var(--color-cocoa-text)] mb-3">
            Governance & Legal
          </h4>
          <ul className="space-y-2 text-xs">
            <li>
              <button onClick={() => openModal('privacy')} className="flex items-center gap-1.5 text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                <ShieldCheck className="w-3.5 h-3.5" />
                Privacy Policy Modal
              </button>
            </li>
            <li>
              <button onClick={() => openModal('terms')} className="flex items-center gap-1.5 text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                <FileText className="w-3.5 h-3.5" />
                Terms of Research License
              </button>
            </li>
            <li>
              <button onClick={() => setActiveView('faq')} className="flex items-center gap-1.5 text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                <HelpCircle className="w-3.5 h-3.5" />
                FAQ (MIA AUROC & k-anonymity)
              </button>
            </li>
            <li>
              <a href="/sitemap.xml" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-[var(--color-cocoa-subtext)] hover:text-[#6B1D2F] transition-colors">
                <ExternalLink className="w-3.5 h-3.5" />
                Sitemap.xml
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto mt-8 pt-6 border-t border-[var(--color-border-subtle)] text-center text-[11px] text-[var(--color-cocoa-subtext)]">
        © 2026 Synora Synthetic Patient Cohort Platform. Built with Terracotta Wine design system for biomedical researchers.
      </div>
    </footer>
  );
}
