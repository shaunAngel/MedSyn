import React, { useState, useRef, useEffect } from 'react';
import {
  Sun, Moon, Dna, ShieldCheck, Database, Sliders,
  FileSpreadsheet, Download, HelpCircle, User,
  Search, ChevronLeft, ChevronRight, LogOut
} from 'lucide-react';

// ─── Workflow steps shown in sub-bar (excludes Landing & FAQ from pill row)
const WORKFLOW_STEPS = [
  { id: 'dataset-dna',      label: 'Dataset DNA',         icon: Database,       step: 1 },
  { id: 'cohort-designer',  label: 'Cohort Designer',     icon: Sliders,        step: 2 },
  { id: 'trust-report',     label: 'Why Trust This?',     icon: ShieldCheck,    step: 3 },
  { id: 'explorer',         label: 'Population Explorer', icon: FileSpreadsheet, step: 4 },
  { id: 'export-hub',       label: 'Export Hub',          icon: Download,       step: 5 },
  { id: 'faq',              label: 'FAQ',                 icon: HelpCircle,     step: 6 },
];

export default function Navbar({ activeView, setActiveView, darkMode, setDarkMode, user, openAuthModal, onSignOut }) {
  const [searchVal, setSearchVal] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const scrollRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Determine if sub-bar should be visible (everything except landing)
  const showSubBar = activeView !== 'landing';

  // Track scroll shadows for the pill sub-bar
  const checkScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  };

  useEffect(() => {
    checkScroll();
    const el = scrollRef.current;
    if (el) el.addEventListener('scroll', checkScroll, { passive: true });
    window.addEventListener('resize', checkScroll);
    return () => {
      if (el) el.removeEventListener('scroll', checkScroll);
      window.removeEventListener('resize', checkScroll);
    };
  }, [showSubBar]);

  // Scroll the pill bar by a fixed amount
  const scrollPills = (dir) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 200, behavior: 'smooth' });
  };

  // Quick-search: jump to view by keyword
  const handleSearchKey = (e) => {
    if (e.key !== 'Enter' || !searchVal.trim()) return;
    const q = searchVal.toLowerCase();
    const match = WORKFLOW_STEPS.find(s =>
      s.label.toLowerCase().includes(q) || s.id.includes(q)
    );
    if (match) { setActiveView(match.id); setSearchVal(''); }
  };

  return (
    <header
      id="synora-header"
      className="sticky top-0 z-40 transition-colors"
      style={{ background: 'var(--color-cream-canvas)' }}
    >
      {/* ════════════════════════════════════════════════
          TIER 1 — Global Top Header
      ════════════════════════════════════════════════ */}
      <div
        className="border-b"
        style={{ borderColor: 'var(--color-border-subtle)', background: 'var(--color-cream-canvas)' }}
      >
        <div className="max-w-screen-xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">

          {/* Brand Logo */}
          <button
            onClick={() => setActiveView('landing')}
            className="flex items-center gap-3 shrink-0 focus:outline-none group"
            aria-label="Go to Synora Home"
          >
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform"
              style={{ background: 'linear-gradient(135deg, #8B263E, #6B1D2F)' }}
            >
              <Dna className="w-5 h-5" style={{ animation: 'pulse 2s infinite' }} />
            </div>
            <div className="leading-tight">
              <span
                className="block font-serif text-xl font-bold tracking-tight"
                style={{ color: 'var(--color-cocoa-text)' }}
              >
                Synora
              </span>
              <span
                className="block text-[9px] font-semibold tracking-widest uppercase"
                style={{ color: '#6B1D2F' }}
              >
                Synthetic Cohort Platform
              </span>
            </div>
          </button>

          {/* Quick Search — center */}
          <div
            className="hidden sm:flex items-center gap-2 flex-1 max-w-xs rounded-xl border px-3 py-2 transition-all"
            style={{
              borderColor: searchFocused ? '#6B1D2F' : 'var(--color-border-subtle)',
              background: 'var(--color-card-white)',
              boxShadow: searchFocused ? '0 0 0 3px rgba(107,29,47,0.10)' : 'none',
            }}
          >
            <Search className="w-3.5 h-3.5 shrink-0" style={{ color: '#6B1D2F' }} />
            <input
              id="synora-quick-search"
              type="text"
              value={searchVal}
              onChange={e => setSearchVal(e.target.value)}
              onKeyDown={handleSearchKey}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              placeholder="Jump to a view… (Enter)"
              className="bg-transparent text-xs w-full focus:outline-none placeholder-gray-400"
              style={{ color: 'var(--color-cocoa-text)' }}
              aria-label="Quick search to jump to a view"
            />
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2 shrink-0">

            {/* Dark Mode Toggle */}
            <button
              id="dark-mode-toggle"
              onClick={() => setDarkMode(!darkMode)}
              className="w-9 h-9 rounded-xl border flex items-center justify-center transition-all hover:scale-105"
              style={{
                borderColor: 'var(--color-border-subtle)',
                background: 'var(--color-card-white)',
              }}
              aria-label={`Switch to ${darkMode ? 'Light Mode' : 'Dark Mode'}`}
              title={`Switch to ${darkMode ? 'Light Mode' : 'Dark Mode'}`}
            >
              {darkMode
                ? <Sun className="w-4 h-4 text-amber-400" />
                : <Moon className="w-4 h-4" style={{ color: '#6B1D2F' }} />
              }
            </button>

            {/* Auth Buttons / User Chip */}
            {user ? (
              <div className="flex items-center gap-1.5">
                <div
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold"
                  style={{
                    borderColor: 'var(--color-border-subtle)',
                    background: 'var(--color-cream-surface)',
                    color: 'var(--color-cocoa-text)',
                  }}
                >
                  <User className="w-3.5 h-3.5" style={{ color: '#6B1D2F' }} />
                  <span className="truncate max-w-[100px]">{user.name}</span>
                </div>
                {onSignOut && (
                  <button
                    onClick={onSignOut}
                    className="w-9 h-9 rounded-xl border flex items-center justify-center transition-all hover:scale-105"
                    style={{ borderColor: 'var(--color-border-subtle)', background: 'var(--color-card-white)' }}
                    title="Sign Out"
                    aria-label="Sign Out"
                  >
                    <LogOut className="w-4 h-4" style={{ color: '#6B1D2F' }} />
                  </button>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  id="nav-sign-in"
                  onClick={() => openAuthModal('signin')}
                  className="px-3.5 py-2 text-xs font-semibold rounded-xl border transition-all hover:bg-[#6B1D2F]/5"
                  style={{
                    borderColor: 'var(--color-border-subtle)',
                    color: 'var(--color-cocoa-text)',
                  }}
                >
                  Sign In
                </button>
                <button
                  id="nav-sign-up"
                  onClick={() => openAuthModal('signup')}
                  className="px-4 py-2 text-xs font-semibold text-white rounded-xl shadow-md transition-all hover:scale-105"
                  style={{ background: 'linear-gradient(135deg, #8B263E, #6B1D2F)' }}
                >
                  Sign Up
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ════════════════════════════════════════════════
          TIER 2 — Contextual Workflow Sub-Bar
          Visible on every view EXCEPT landing
      ════════════════════════════════════════════════ */}
      {showSubBar && (
        <div
          className="border-b relative"
          style={{
            borderColor: 'var(--color-border-subtle)',
            background: 'var(--color-cream-surface, #F5EEE6)',
          }}
        >
          <div className="max-w-screen-xl mx-auto px-4 sm:px-6 flex items-center h-11 gap-1">

            {/* Left scroll shadow + button */}
            {canScrollLeft && (
              <button
                onClick={() => scrollPills(-1)}
                className="absolute left-0 z-10 h-11 px-1.5 flex items-center"
                style={{
                  background: 'linear-gradient(to right, var(--color-cream-surface, #F5EEE6) 60%, transparent)',
                }}
                aria-label="Scroll navigation left"
              >
                <ChevronLeft className="w-4 h-4" style={{ color: 'var(--color-cocoa-subtext)' }} />
              </button>
            )}

            {/* Pill Row */}
            <nav
              ref={scrollRef}
              id="synora-workflow-subnav"
              className="flex items-center gap-1 overflow-x-auto scrollbar-hide w-full"
              style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
              role="navigation"
              aria-label="Workflow steps navigation"
            >
              {WORKFLOW_STEPS.map((step) => {
                const Icon = step.icon;
                const isActive = activeView === step.id;
                return (
                  <button
                    key={step.id}
                    id={`subnav-${step.id}`}
                    onClick={() => setActiveView(step.id)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap shrink-0 transition-all"
                    style={
                      isActive
                        ? {
                            background: '#6B1D2F',
                            color: '#ffffff',
                            boxShadow: '0 1px 6px rgba(107,29,47,0.25)',
                          }
                        : {
                            background: 'transparent',
                            color: 'var(--color-cocoa-subtext)',
                          }
                    }
                    onMouseEnter={e => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'rgba(107,29,47,0.07)';
                        e.currentTarget.style.color = 'var(--color-cocoa-text)';
                      }
                    }}
                    onMouseLeave={e => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--color-cocoa-subtext)';
                      }
                    }}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    {/* Step number badge */}
                    <span
                      className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold leading-none shrink-0"
                      style={{
                        background: isActive ? 'rgba(255,255,255,0.25)' : 'rgba(107,29,47,0.10)',
                        color: isActive ? '#ffffff' : '#6B1D2F',
                      }}
                    >
                      {step.step}
                    </span>
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span>{step.label}</span>
                  </button>
                );
              })}
            </nav>

            {/* Right scroll shadow + button */}
            {canScrollRight && (
              <button
                onClick={() => scrollPills(1)}
                className="absolute right-0 z-10 h-11 px-1.5 flex items-center"
                style={{
                  background: 'linear-gradient(to left, var(--color-cream-surface, #F5EEE6) 60%, transparent)',
                }}
                aria-label="Scroll navigation right"
              >
                <ChevronRight className="w-4 h-4" style={{ color: 'var(--color-cocoa-subtext)' }} />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Mobile bottom bar — always visible, icon-only on tiny screens */}
      <div
        className="sm:hidden flex items-center justify-around border-t px-2 py-2 overflow-x-auto"
        style={{ borderColor: 'var(--color-border-subtle)', background: 'var(--color-cream-surface, #F5EEE6)' }}
      >
        {WORKFLOW_STEPS.map((step) => {
          const Icon = step.icon;
          const isActive = activeView === step.id;
          return (
            <button
              key={step.id}
              onClick={() => setActiveView(step.id)}
              className="flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-xl text-[9px] font-semibold shrink-0 transition-colors"
              style={{ color: isActive ? '#6B1D2F' : 'var(--color-cocoa-subtext)' }}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className="w-4 h-4" />
              <span className="leading-tight text-center">{step.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
}
