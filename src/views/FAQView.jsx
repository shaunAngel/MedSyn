import React, { useState } from 'react';
import { HelpCircle, ChevronDown, ShieldCheck, Sliders, Dna, Database } from 'lucide-react';

export default function FAQView() {
  const [openIdx, setOpenIdx] = useState(0);

  const faqs = [
    {
      q: 'How does SDV Gaussian Copula longitudinal synthesis work in Synora?',
      a: 'Synora fits a Gaussian Copula model on continuous and categorical features after applying a Probability Integral Transform (PIT) to map marginal distributions to standard normal space. For longitudinal data, static baseline features and monthly dynamics are modeled to sample 6-month patient trajectories (3,000 rows across 500 synthetic patients).'
    },
    {
      q: 'What is a Membership Inference Attack (MIA) and how is AUROC interpreted?',
      a: 'An MIA shadow model attempts to determine whether a given target patient was included in the model training set. An MIA AUROC score of ~0.50 means the attack is equivalent to random guessing (optimal privacy). AUROC scores between 0.48 and 0.60 indicate strong privacy protection. If MIA AUROC ≥ 0.75, the Privacy Gate automatically blocks dataset export.'
    },
    {
      q: 'What is k-anonymity and why are singletons (k=1) flagged as privacy risks?',
      a: 'k-anonymity requires that every individual in a dataset is indistinguishable from at least k-1 other individuals with respect to quasi-identifiers (such as age, gender, ethnicity, and diabetic status). If k_min = 1, at least one singleton patient has a unique combination of traits, posing a re-identification risk. The Privacy Gate requires k_min > 1.'
    },
    {
      q: 'How do the Dual Symmetric Gates operate?',
      a: 'The Feasibility Gate checks source evidence count before generation, requiring explicit researcher confirmation if matching source rows < 3. The Privacy Gate checks privacy metrics after generation, automatically blocking download if MIA AUROC ≥ 0.75 or k_min = 1.'
    },
    {
      q: 'Is any Protected Health Information (PHI) stored or exported?',
      a: 'No. Synora processes ground-truth source data locally to extract statistics and copula parameters. No raw patient IDs or real-world PHI are ever exported or transmitted outside your workspace.'
    }
  ];

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-8 animate-fade-in">
      
      {/* Header */}
      <div className="border-b border-[var(--color-border-subtle)] pb-6 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] text-xs font-bold mb-2">
          <HelpCircle className="w-3.5 h-3.5" />
          <span>METHODOLOGY &amp; FREQUENTLY ASKED QUESTIONS</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
          Frequently Asked Questions
        </h1>
        <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
          Deep dive into Gaussian Copula synthesis, MIA AUROC scoring, k-anonymity, and symmetric gates.
        </p>
      </div>

      {/* Accordion List */}
      <div className="space-y-4">
        {faqs.map((faq, idx) => {
          const isOpen = openIdx === idx;
          return (
            <div
              key={idx}
              className="rounded-[20px] bg-[var(--color-card-white)] border border-[var(--color-border-subtle)] overflow-hidden shadow-md transition-all"
            >
              <button
                onClick={() => setOpenIdx(isOpen ? null : idx)}
                className="w-full text-left p-5 flex items-center justify-between gap-4 font-serif font-bold text-sm text-[var(--color-cocoa-text)] focus:outline-none"
              >
                <span>{faq.q}</span>
                <ChevronDown className={`w-5 h-5 text-[#6B1D2F] shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </button>

              {isOpen && (
                <div className="px-5 pb-5 text-xs leading-relaxed text-[var(--color-cocoa-subtext)] border-t border-[var(--color-border-subtle)] pt-4 animate-fade-in">
                  {faq.a}
                </div>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
}
