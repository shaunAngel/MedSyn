import React from 'react';
import { AlertTriangle } from 'lucide-react';

export default function WarningBanner() {
  return (
    <div 
      className="w-full bg-[#6B1D2F] text-[#FDF8F2] px-4 py-2.5 text-xs sm:text-sm font-medium flex items-center justify-center gap-2 shadow-md relative z-50 border-b border-[#8B263E]"
      role="banner"
      aria-label="Research Disclaimer Warning"
    >
      <AlertTriangle className="w-4 h-4 text-[#E89B72] shrink-0" aria-hidden="true" />
      <span className="text-center">
        <strong>⚠️ For research and testing purposes only.</strong> Not clinically validated. No formal differential privacy applied.
      </span>
    </div>
  );
}
