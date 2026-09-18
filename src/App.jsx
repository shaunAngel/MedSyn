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
  
  const [legalModal, setLegalModal] = useState(null); // 'privacy' or 'terms'
  
  const [stepperOpen, setStepperOpen] = useState(false);
  const [generationConfig, setGenerationConfig] = useState(null);

  // Apply Dark Mode data-theme attribute
  useEffect(() => {
    if (darkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('synora_theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('synora_theme', 'light');
    }
  }, [darkMode]);

  // Analytics Hook & Meta Title/Description updates per view state
  useEffect(() => {
    const titles = {
      'landing': 'Synora | Synthetic Patient Cohort Platform',
      'dataset-dna': 'Synora | Dataset DNA Intelligence',
      'cohort-designer': 'Synora | Cohort Designer & Feasibility Gate',
      'trust-report': 'Synora | Why Trust This? Validation Report',
      'explorer': 'Synora | Population Explorer & Trajectories',
      'export-hub': 'Synora | Export Hub & Privacy Certificate',
      'faq': 'Synora | Frequently Asked Questions',
      '404': 'Synora | Page Not Found'
    };

    const descriptions = {
      'landing': 'Synora is the researcher-first decision layer enforcing symmetric feasibility and privacy gates on synthetic patient data.',
      'dataset-dna': 'Explore ground-truth dataset schema, row counts, and sparsity health metrics prior to synthetic generation.',
      'cohort-designer': 'Design target patient cohorts with real-time Feasibility Gate evidence validation and sparse confirmation locks.',
      'trust-report': 'Review empirical copula fidelity, Activity-Pain correlation, and shadow Membership Inference Attack scores.',
      'explorer': 'Inspect individual 6-month longitudinal clinical patient trajectories.',
      'export-hub': 'Download certified synthetic datasets bundled with cryptographically verifiable privacy certificates.',
      'faq': 'Methodology guide on Gaussian Copula longitudinal synthesis, MIA AUROC scoring, and k-anonymity.',
      '404': 'Requested research view was not found.'
    };

    document.title = titles[activeView] || titles['landing'];
    
    let metaDesc = document.querySelector('meta[name="description"]');
    if (!metaDesc) {
      metaDesc = document.createElement('meta');
      metaDesc.name = 'description';
      document.head.appendChild(metaDesc);
    }
    metaDesc.content = descriptions[activeView] || descriptions['landing'];

    // Analytics event logging hook
    console.log(`[Synora Analytics] Navigated to view: ${activeView}`);
  }, [activeView]);

  const openAuthModal = (mode = 'signin') => {
    setAuthMode(mode);
    setAuthModalOpen(true);
  };

  const handleStartGeneration = (config) => {
    setGenerationConfig(config);
    setStepperOpen(true);
  };

  const handleGenerationComplete = (payload) => {
    setStepperOpen(false);
    setActiveView('trust-report');
  };

  const handleGenerationError = (err) => {
    setStepperOpen(false);
    alert('Generation Error: Feasibility Gate or Copula synthesis failed.');
  };

  const renderView = () => {
    switch (activeView) {
      case 'landing':
        return <LandingPage setActiveView={setActiveView} openAuthModal={openAuthModal} />;
      case 'dataset-dna':
        return <DatasetDNAView setActiveView={setActiveView} />;
      case 'cohort-designer':
        return <CohortDesignerView onStartGeneration={handleStartGeneration} />;
      case 'trust-report':
        return <TrustReportView setActiveView={setActiveView} />;
      case 'explorer':
        return <PopulationExplorerView />;
      case 'export-hub':
        return <ExportHubView />;
      case 'faq':
        return <FAQView />;
      default:
        return <NotFoundView setActiveView={setActiveView} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-cream-canvas)] text-[var(--color-cocoa-text)]">
      
      {/* 1. Mandatory Warning Banner on top of EVERY screen */}
      <WarningBanner />

      {/* 2. Primary Navigation Header */}
      <Navbar
        activeView={activeView}
        setActiveView={setActiveView}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        user={user}
        openAuthModal={openAuthModal}
      />

      {/* 3. Main Content View Area */}
      <main className="flex-1">
        {renderView()}
      </main>

      {/* 4. Footer */}
      <Footer openModal={(type) => setLegalModal(type)} setActiveView={setActiveView} />

      {/* 5. Modals & Infrastructure Overlays */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authMode}
        onSuccess={(u) => setUser(u)}
      />

      <PrivacyTermsModals
        activeModal={legalModal}
        onClose={() => setLegalModal(null)}
      />

      <GenerationStepperModal
        isOpen={stepperOpen}
        config={generationConfig}
        onComplete={handleGenerationComplete}
        onError={handleGenerationError}
      />

      {/* 6. Cookie Consent Banner */}
      <CookieBanner />

    </div>
  );
}
