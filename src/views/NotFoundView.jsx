import React from 'react';
import { AlertTriangle, ArrowLeft } from 'lucide-react';

export default function NotFoundView({ setActiveView }) {
  return (
    <div className="py-24 px-4 text-center space-y-6 max-w-md mx-auto animate-fade-in">
      <div className="w-16 h-16 rounded-3xl bg-[var(--color-coral-bg)] text-[var(--color-coral-risk)] border border-[var(--color-coral-risk)]/30 flex items-center justify-center mx-auto shadow-xl">
        <AlertTriangle className="w-8 h-8" />
      </div>

      <div className="space-y-2">
        <span className="font-mono text-xs font-bold text-[#6B1D2F] dark:text-[#E89B72] tracking-widest uppercase">
          ERROR 404 • ROUTE UNMAPPED
        </span>
        <h1 className="font-serif text-3xl font-bold text-[var(--color-cocoa-text)]">
          Page Not Found
        </h1>
        <p className="text-xs text-[var(--color-cocoa-subtext)]">
          The requested research view or route does not exist in the Synora decision engine.
        </p>
      </div>

      <button
        onClick={() => setActiveView('landing')}
        className="px-6 py-3 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-xs font-bold rounded-xl shadow-lg transition-all hover:scale-105 inline-flex items-center gap-2"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Return to Home Landing Page</span>
      </button>
    </div>
  );
}
