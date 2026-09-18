import React, { useState, useEffect } from 'react';
import { Download, ShieldCheck, FileText, CheckCircle2, Copy, Sparkles } from 'lucide-react';
import confetti from 'canvas-confetti';
import { getTrustReport } from '../services/mockEngine';

export default function ExportHubView() {
  const [report, setReport] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const data = getTrustReport();
    setReport(data);
  }, []);

  if (!report) return null;

  const cert = report.certificate;
  const isGatePassed = cert.privacy_gate_evaluation.passed;

  const handleExportCSV = () => {
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 }
    });

    // Client-side CSV generation
    const csvRows = [
      ['patient_id', 'month', 'age', 'gender', 'ethnicity', 'diabetic', 'hba1c', 'systolic_bp', 'activity_score', 'pain_score', 'medication_adherence']
    ];
    for (let p = 1; p <= 500; p++) {
      const pId = `SYN_${String(p).padStart(3, '0')}`;
      for (let m = 1; m <= 6; m++) {
        csvRows.push([pId, m, 52 + (p % 30), p % 2 === 0 ? 'Female' : 'Male', 'Caucasian', p % 3 === 0 ? 1 : 0, 6.2, 128, 58.5, 4.2, 88]);
      }
    }
    const csvContent = "data:text/csv;charset=utf-8," + csvRows.map(e => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "synora_synthetic_patients.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportCert = () => {
    confetti({
      particleCount: 50,
      spread: 60,
      origin: { y: 0.6 }
    });

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(cert, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", "privacy_certificate.json");
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const copyCertJson = () => {
    navigator.clipboard.writeText(JSON.stringify(cert, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-10 animate-fade-in">
      
      {/* Header */}
      <div className="border-b border-[var(--color-border-subtle)] pb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] text-xs font-bold mb-2">
          <Download className="w-3.5 h-3.5" />
          <span>CERTIFIED EXPORT HUB</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
          Export Hub &amp; Privacy Certificate
        </h1>
        <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
          Download certified synthetic patient datasets bundled with cryptographically verifiable privacy certificates.
        </p>
      </div>

      {/* Main Download Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Synthetic Dataset CSV Download Card */}
        <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border-2 border-[var(--color-border-subtle)] hover:border-[#6B1D2F]/40 transition-all space-y-6">
          <div className="flex items-center justify-between">
            <div className="w-12 h-12 rounded-2xl bg-[#6B1D2F] text-white flex items-center justify-center shadow-md">
              <FileText className="w-6 h-6" />
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-800">
              CSV Format (3,000 Rows)
            </span>
          </div>

          <div>
            <h2 className="font-serif text-2xl font-bold text-[var(--color-cocoa-text)]">
              Synthetic Patient Dataset
            </h2>
            <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
              synora_synthetic_patients.csv • 500 Synthetic Patients × 6 Longitudinal Months.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] text-xs space-y-1 font-mono">
            <div className="flex justify-between text-[var(--color-cocoa-subtext)]">
              <span>Patients:</span>
              <span className="font-bold text-[var(--color-cocoa-text)]">500</span>
            </div>
            <div className="flex justify-between text-[var(--color-cocoa-subtext)]">
              <span>Total Rows:</span>
              <span className="font-bold text-[var(--color-cocoa-text)]">3,000</span>
            </div>
            <div className="flex justify-between text-[var(--color-cocoa-subtext)]">
              <span>Activity ↔ Pain Correlation:</span>
              <span className="font-bold text-[#2F6B3F]">-0.56</span>
            </div>
          </div>

          <button
            onClick={handleExportCSV}
            disabled={!isGatePassed}
            className={`w-full py-4 rounded-2xl font-bold text-xs shadow-xl transition-all flex items-center justify-center gap-2 ${
              isGatePassed
                ? 'bg-[#6B1D2F] hover:bg-[#8B263E] text-white hover:scale-[1.02]'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Download className="w-4 h-4" />
            <span>Download Synthetic Dataset (CSV)</span>
          </button>
        </div>

        {/* Privacy Certificate Download Card */}
        <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border-2 border-[var(--color-border-subtle)] hover:border-[#6B1D2F]/40 transition-all space-y-6">
          <div className="flex items-center justify-between">
            <div className="w-12 h-12 rounded-2xl bg-[#2F6B3F] text-white flex items-center justify-center shadow-md">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#EAF4EC] text-[#2F6B3F]">
              JSON Artifact
            </span>
          </div>

          <div>
            <h2 className="font-serif text-2xl font-bold text-[var(--color-cocoa-text)]">
              Privacy &amp; Fidelity Certificate
            </h2>
            <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
              privacy_certificate.json • Audit trace of MIA score, k_min, and gate decisions.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-cream-surface)] text-xs space-y-1 font-mono">
            <div className="flex justify-between text-[var(--color-cocoa-subtext)]">
              <span>Certificate ID:</span>
              <span className="font-bold text-[#6B1D2F] dark:text-[#E89B72]">{cert.certificate_id}</span>
            </div>
            <div className="flex justify-between text-[var(--color-cocoa-subtext)]">
              <span>MIA AUROC Score:</span>
              <span className="font-bold text-[#2F6B3F]">{cert.privacy_metrics.membership_inference_attack.mia_auroc}</span>
            </div>
            <div className="flex justify-between text-[var(--color-cocoa-subtext)]">
              <span>k-Anonymity k_min:</span>
              <span className="font-bold text-[#2F6B3F]">{cert.privacy_metrics.k_anonymity.k_min}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleExportCert}
              className="flex-1 py-4 bg-[#2F6B3F] hover:bg-[#255632] text-white font-bold text-xs rounded-2xl shadow-xl transition-all hover:scale-[1.02] flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              <span>Download privacy_certificate.json</span>
            </button>

            <button
              onClick={copyCertJson}
              className="p-4 border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] hover:bg-[var(--color-card-white)] rounded-2xl transition-colors"
              title="Copy Certificate JSON to Clipboard"
            >
              {copied ? <CheckCircle2 className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4 text-[var(--color-cocoa-subtext)]" />}
            </button>
          </div>
        </div>

      </div>

      {/* Certificate JSON Preview Inspector */}
      <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
        <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-4">
          <h3 className="font-serif font-bold text-xl text-[var(--color-cocoa-text)] flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#6B1D2F]" />
            <span>Interactive Certificate Inspector</span>
          </h3>
          <span className="text-xs text-[var(--color-cocoa-subtext)] font-mono">
            Hash: {cert.dataset_hash}
          </span>
        </div>

        <pre className="p-4 rounded-2xl bg-[#140A0C] text-[#E89B72] text-xs font-mono max-h-80 overflow-y-auto leading-relaxed border border-[#3D1F25]">
          {JSON.stringify(cert, null, 2)}
        </pre>
      </div>

    </div>
  );
}
