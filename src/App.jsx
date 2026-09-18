import React, { useState, useEffect } from 'react';
import WarningBanner from './components/WarningBanner';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import AuthModal from './components/AuthModal';
import CookieBanner from './components/CookieBanner';
import PrivacyTermsModals from './components/PrivacyTermsModals';

import LandingPage from './views/LandingPage';
import DatasetDNAView from './views/DatasetDNAView';
import CohortDesignerView from './views/CohortDesignerView';
import GenerationStepperModal from './views/GenerationStepperModal';
import TrustReportView from './views/TrustReportView';
import PopulationExplorerView from './views/PopulationExplorerView';
import ExportHubView from './views/ExportHubView';
import FAQView from './views/FAQView';
import NotFoundView from './views/NotFoundView';

export default function App() {
  const [activeView, setActiveView] = useState('landing');

  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('synora_theme') === 'dark';
  });

  const [user, setUser] = useState(null);

  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState('signin');

  const [legalModal, setLegalModal] = useState(null);

  const [stepperOpen, setStepperOpen] = useState(false);
  const [generationConfig, setGenerationConfig] = useState(null);

  // Stores the latest successful backend generation result.
  // Views can retrieve the full result again through src/services/api.js.
  const [generationResult, setGenerationResult] = useState(null);

  // ---------------------------------------------------------------------------
  // Dark mode
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (darkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('synora_theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('synora_theme', 'light');
    }
  }, [darkMode]);

  // ---------------------------------------------------------------------------
  // Page metadata
  // ---------------------------------------------------------------------------

  useEffect(() => {
    const titles = {
      landing: 'Synora | Synthetic Patient Cohort Platform',
      'dataset-dna': 'Synora | Dataset DNA Intelligence',
      'cohort-designer': 'Synora | Cohort Designer & Feasibility Gate',
      'trust-report': 'Synora | Why Trust This? Validation Report',
      explorer: 'Synora | Population Explorer & Trajectories',
      'export-hub': 'Synora | Export Hub & Privacy Certificate',
      faq: 'Synora | Frequently Asked Questions',
      404: 'Synora | Page Not Found'
    };

    const descriptions = {
      landing:
          'Synora is the researcher-first decision layer enforcing symmetric feasibility and privacy gates on synthetic patient data.',

      'dataset-dna':
          'Explore ground-truth dataset schema, row counts, and sparsity health metrics prior to synthetic generation.',

      'cohort-designer':
          'Design target patient cohorts with real-time Feasibility Gate evidence validation and sparse confirmation locks.',

      'trust-report':
          'Review empirical copula fidelity, Activity-Pain correlation, and shadow Membership Inference Attack scores.',

      explorer:
          'Inspect individual 6-month longitudinal clinical patient trajectories.',

      'export-hub':
          'Download certified synthetic datasets bundled with cryptographically verifiable privacy certificates.',

      faq:
          'Methodology guide on Gaussian Copula longitudinal synthesis, MIA AUROC scoring, and k-anonymity.',

      404:
          'Requested research view was not found.'
    };

    document.title = titles[activeView] || titles.landing;

    let metaDesc = document.querySelector('meta[name="description"]');

    if (!metaDesc) {
      metaDesc = document.createElement('meta');
      metaDesc.name = 'description';
      document.head.appendChild(metaDesc);
    }

    metaDesc.content =
        descriptions[activeView] || descriptions.landing;

    console.log(
        `[Synora Analytics] Navigated to view: ${activeView}`
    );
  }, [activeView]);

  // ---------------------------------------------------------------------------
  // Authentication
  // ---------------------------------------------------------------------------

  const openAuthModal = (mode = 'signin') => {
    setAuthMode(mode);
    setAuthModalOpen(true);
  };

  // ---------------------------------------------------------------------------
  // Generation lifecycle
  // ---------------------------------------------------------------------------

  const handleStartGeneration = (config) => {
    setGenerationConfig(config);
    setStepperOpen(true);
  };

  const handleGenerationComplete = (payload) => {
    console.log('[Synora] Generation completed:', payload);

    setGenerationResult(payload);
    setStepperOpen(false);

    // Move directly to the evidence/trust layer after generation.
    setActiveView('trust-report');
  };

  const handleGenerationError = (err) => {
    console.error('[Synora] Generation failed:', err);

    setStepperOpen(false);

    const message =
        err?.message ||
        err?.response?.data?.detail ||
        'Generation failed. Please check the Feasibility Gate and backend connection.';

    alert(`Generation Error: ${message}`);
  };

  // ---------------------------------------------------------------------------
  // View router
  // ---------------------------------------------------------------------------

  const renderView = () => {
    switch (activeView) {
      case 'landing':
        return (
            <LandingPage
                setActiveView={setActiveView}
                openAuthModal={openAuthModal}
            />
        );

      case 'dataset-dna':
        return (
            <DatasetDNAView
                setActiveView={setActiveView}
            />
        );

      case 'cohort-designer':
        return (
            <CohortDesignerView
                onStartGeneration={handleStartGeneration}
            />
        );

      case 'trust-report':
        return (
            <TrustReportView
                setActiveView={setActiveView}
                generationResult={generationResult}
            />
        );

      case 'explorer':
        return <PopulationExplorerView />;

      case 'export-hub':
        return <ExportHubView />;

      case 'faq':
        return <FAQView />;

      default:
        return (
            <NotFoundView
                setActiveView={setActiveView}
            />
        );
    }
  };

  // ---------------------------------------------------------------------------
  // Application shell
  // ---------------------------------------------------------------------------

  return (
      <div className="min-h-screen flex flex-col bg-[var(--color-cream-canvas)] text-[var(--color-cocoa-text)]">

        {/* Mandatory Warning Banner */}
        <WarningBanner />

        {/* Primary Navigation */}
        <Navbar
            activeView={activeView}
            setActiveView={setActiveView}
            darkMode={darkMode}
            setDarkMode={setDarkMode}
            user={user}
            openAuthModal={openAuthModal}
        />

        {/* Main Content */}
        <main className="flex-1">
          {renderView()}
        </main>

        {/* Footer */}
        <Footer
            openModal={(type) => setLegalModal(type)}
            setActiveView={setActiveView}
        />

        {/* Authentication */}
        <AuthModal
            isOpen={authModalOpen}
            onClose={() => setAuthModalOpen(false)}
            initialMode={authMode}
            onSuccess={(u) => setUser(u)}
        />

        {/* Privacy / Terms */}
        <PrivacyTermsModals
            activeModal={legalModal}
            onClose={() => setLegalModal(null)}
        />

        {/* Synthetic Generation */}
        <GenerationStepperModal
            isOpen={stepperOpen}
            config={generationConfig}
            onComplete={handleGenerationComplete}
            onError={handleGenerationError}
        />

        {/* Cookie Consent */}
        <CookieBanner />

      </div>
  );
}