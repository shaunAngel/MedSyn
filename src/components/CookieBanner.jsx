import React, { useState, useEffect } from 'react';
import { Cookie, X, Check } from 'lucide-react';

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('synora_cookie_consent');
    if (!consent) {
      setVisible(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('synora_cookie_consent', 'accepted');
    setVisible(false);
  };

  const handleDecline = () => {
    localStorage.setItem('synora_cookie_consent', 'essential_only');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:max-w-md z-40 bg-[var(--color-card-white)] rounded-[20px] p-5 shadow-2xl border border-[var(--color-border-subtle)] text-[var(--color-cocoa-text)] animate-fade-in">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-xl bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] shrink-0">
          <Cookie className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h4 className="text-xs font-bold font-serif">Research Data & Cookie Preferences</h4>
          <p className="text-[11px] text-[var(--color-cocoa-subtext)] mt-1">
            Synora uses essential local session storage to persist cohort filter states and privacy certificates. No personal tracking telemetry is sold.
          </p>
          <div className="flex items-center gap-2 mt-3">
            <button
              onClick={handleAccept}
              className="px-3.5 py-1.5 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-[11px] font-bold rounded-lg shadow-sm transition-all"
            >
              Accept All
            </button>
            <button
              onClick={handleDecline}
              className="px-3 py-1.5 border border-[var(--color-border-subtle)] hover:bg-[var(--color-cream-surface)] text-[11px] font-semibold rounded-lg transition-colors"
            >
              Essential Only
            </button>
          </div>
        </div>
        <button
          onClick={handleDecline}
          className="text-[var(--color-cocoa-subtext)] hover:text-[var(--color-cocoa-text)] p-1"
          aria-label="Dismiss cookie banner"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
