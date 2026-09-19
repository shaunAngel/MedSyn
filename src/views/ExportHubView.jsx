import React, { useEffect, useState } from 'react';
import {
  Download,
  ShieldCheck,
  FileText,
  CheckCircle2,
  Copy,
  LockKeyhole,
  Fingerprint,
  Database,
  Activity,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { getTrustReport } from '../services/api';

export default function ExportHubView() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let mounted = true;

    const loadReport = async () => {
      try {
        const data = await getTrustReport();

        if (mounted) {
          setReport(data);
        }
      } catch (error) {
        console.error('[Synora] Failed to load certificate:', error);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadReport();

    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return (
        <div className="min-h-[60vh] flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 rounded-full border-4 border-[#6B1D2F]/20 border-t-[#6B1D2F] animate-spin mx-auto mb-4" />
            <p className="text-sm text-[var(--color-cocoa-subtext)]">
              Preparing your privacy certificate...
            </p>
          </div>
        </div>
    );
  }

  if (!report?.certificate) {
    return (
        <div className="max-w-3xl mx-auto py-20 px-6 text-center">
          <AlertTriangle className="w-10 h-10 mx-auto mb-4 text-[#8B263E]" />
          <h2 className="font-serif text-2xl font-bold text-[var(--color-cocoa-text)]">
            No certificate available
          </h2>
          <p className="text-sm text-[var(--color-cocoa-subtext)] mt-2">
            Generate a synthetic cohort first, then return here to view its
            certificate.
          </p>
        </div>
    );
  }

  const cert = report.certificate;

  const privacyMetrics = cert.privacy_metrics || {};
  const mia =
      privacyMetrics.membership_inference_attack ||
      cert.membership_inference ||
      {};

  const kAnon =
      privacyMetrics.k_anonymity ||
      cert.k_anonymity ||
      {};

  const gate =
      cert.privacy_gate_evaluation ||
      cert.privacy_gate ||
      {};

  const dcr =
      privacyMetrics.dcr ||
      cert.dcr ||
      {};

  const stats = cert.dataset_statistics || {};
  const fidelity = cert.fidelity_metrics || {};
  const correlation = fidelity.activity_pain_correlation || {};

  const isGatePassed =
      gate.passed === true ||
      gate.status === 'Pass' ||
      gate.tier === 'Pass';

  const miaValue =
      mia.attack_auroc ??
      mia.mia_auroc ??
      mia.auroc;

  const kValue =
      kAnon.k_min ??
      kAnon.k;

  const qualityValue =
      fidelity.fidelity_score ??
      (fidelity.quality_score != null
          ? Number(fidelity.quality_score) * 100
          : null);

  const generatedAt =
      cert.timestamp ||
      cert.generated_at;

  const formattedDate = generatedAt
      ? new Date(generatedAt).toLocaleString([], {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
      : '—';

  const handleExport = async () => {
    if (!isGatePassed) return;

    setExporting(true);

    try {
      const response = await fetch(
          'http://localhost:8000/api/export'
      );

      if (!response.ok) {
        throw new Error(
            `Export failed with status ${response.status}`
        );
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = 'synora_synthetic_cohort_export.zip';

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      confetti({
        particleCount: 100,
        spread: 75,
        origin: { y: 0.65 },
      });
    } catch (error) {
      console.error('[Synora] Export failed:', error);
      alert(
          'Export could not be completed. Make sure the Synora backend is running.'
      );
    } finally {
      setExporting(false);
    }
  };

  const handleExportCert = () => {
    const dataStr =
        'data:application/json;charset=utf-8,' +
        encodeURIComponent(
            JSON.stringify(cert, null, 2)
        );

    const downloadAnchor =
        document.createElement('a');

    downloadAnchor.setAttribute(
        'href',
        dataStr
    );

    downloadAnchor.setAttribute(
        'download',
        'privacy_certificate.json'
    );

    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    confetti({
      particleCount: 50,
      spread: 60,
      origin: { y: 0.6 },
    });
  };

  const copyCertJson = async () => {
    try {
      await navigator.clipboard.writeText(
          JSON.stringify(cert, null, 2)
      );

      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (error) {
      console.error(
          '[Synora] Could not copy certificate:',
          error
      );
    }
  };

  const MetricCard = ({
                        icon: Icon,
                        label,
                        value,
                        description,
                        accent = 'maroon',
                      }) => (
      <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-white p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.16em] font-bold text-[var(--color-cocoa-subtext)]">
              {label}
            </p>

            <p className="mt-2 text-2xl font-bold text-[var(--color-cocoa-text)]">
              {value}
            </p>
          </div>

          <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  accent === 'green'
                      ? 'bg-[#EAF4EC] text-[#2F6B3F]'
                      : 'bg-[#6B1D2F]/10 text-[#6B1D2F]'
              }`}
          >
            <Icon className="w-5 h-5" />
          </div>
        </div>

        {description && (
            <p className="text-[11px] leading-relaxed text-[var(--color-cocoa-subtext)] mt-3">
              {description}
            </p>
        )}
      </div>
  );

  return (
      <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto space-y-8 animate-fade-in">

        {/* ========================================================= */}
        {/* PAGE HEADER */}
        {/* ========================================================= */}

        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6B1D2F]/10 text-[#6B1D2F] text-xs font-bold mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            CERTIFIED EXPORT HUB
          </div>

          <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
            Privacy &amp; Fidelity Certificate
          </h1>

          <p className="text-sm text-[var(--color-cocoa-subtext)] mt-2 max-w-3xl">
            A human-readable record of how this synthetic cohort was generated,
            evaluated, and cleared for export.
          </p>
        </div>

        {/* ========================================================= */}
        {/* CERTIFICATE */}
        {/* ========================================================= */}

        <div className="relative overflow-hidden rounded-[32px] border-2 border-[#6B1D2F]/20 bg-white shadow-2xl">

          {/* Decorative top strip */}
          <div className="h-2 bg-gradient-to-r from-[#6B1D2F] via-[#B56A32] to-[#6B1D2F]" />

          <div className="p-6 sm:p-10">

            {/* Certificate heading */}
            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-8">

              <div className="flex items-start gap-4">

                <div className="w-16 h-16 rounded-2xl bg-[#6B1D2F] text-white flex items-center justify-center shadow-lg">
                  <ShieldCheck className="w-8 h-8" />
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#B56A32]">
                    SYNORA
                  </p>

                  <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[var(--color-cocoa-text)] mt-1">
                    Synthetic Patient Cohort
                  </h2>

                  <p className="text-sm text-[var(--color-cocoa-subtext)] mt-1">
                    Privacy &amp; Fidelity Certificate
                  </p>
                </div>

              </div>

              {/* Gate status */}
              <div
                  className={`inline-flex items-center gap-2 self-start px-4 py-2 rounded-full text-xs font-bold ${
                      isGatePassed
                          ? 'bg-[#EAF4EC] text-[#2F6B3F]'
                          : 'bg-[#FFF1E8] text-[#8B263E]'
                  }`}
              >
                {isGatePassed ? (
                    <CheckCircle2 className="w-4 h-4" />
                ) : (
                    <AlertTriangle className="w-4 h-4" />
                )}

                {isGatePassed
                    ? 'PRIVACY GATE PASSED'
                    : 'PRIVACY REVIEW REQUIRED'}
              </div>

            </div>

            {/* Certificate metadata */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">

              <div className="rounded-2xl bg-[var(--color-cream-surface)] p-4">
                <p className="text-[10px] uppercase tracking-wider font-bold text-[var(--color-cocoa-subtext)]">
                  Certificate ID
                </p>

                <p className="font-mono text-xs font-bold text-[#6B1D2F] mt-2 break-all">
                  {cert.certificate_id || '—'}
                </p>
              </div>

              <div className="rounded-2xl bg-[var(--color-cream-surface)] p-4">
                <p className="text-[10px] uppercase tracking-wider font-bold text-[var(--color-cocoa-subtext)]">
                  Generated
                </p>

                <p className="text-sm font-bold text-[var(--color-cocoa-text)] mt-2">
                  {formattedDate}
                </p>
              </div>

              <div className="rounded-2xl bg-[var(--color-cream-surface)] p-4">
                <p className="text-[10px] uppercase tracking-wider font-bold text-[var(--color-cocoa-subtext)]">
                  Dataset Fingerprint
                </p>

                <p className="font-mono text-xs font-bold text-[var(--color-cocoa-text)] mt-2 break-all">
                  {cert.dataset_hash || '—'}
                </p>
              </div>

            </div>

            {/* ===================================================== */}
            {/* DATASET + FIDELITY */}
            {/* ===================================================== */}

            <div className="mt-10">

              <div className="flex items-center gap-3 mb-4">
                <Database className="w-5 h-5 text-[#6B1D2F]" />

                <div>
                  <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
                    Dataset &amp; Fidelity
                  </h3>

                  <p className="text-xs text-[var(--color-cocoa-subtext)]">
                    What was generated and how closely it reflects the source statistics.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

                <MetricCard
                    icon={Database}
                    label="Synthetic Patients"
                    value={
                        stats.synthetic_patients ??
                        report.generated_patients ??
                        '—'
                    }
                    description="Unique synthetic patient profiles generated."
                />

                <MetricCard
                    icon={FileText}
                    label="Total Records"
                    value={
                        stats.total_rows ??
                        report.generated_rows ??
                        '—'
                    }
                    description="Longitudinal synthetic records included in the cohort."
                />

                <MetricCard
                    icon={Activity}
                    label="Fidelity Score"
                    value={
                      qualityValue != null
                          ? `${Number(qualityValue).toFixed(1)}%`
                          : '—'
                    }
                    description="Aggregate statistical quality reported by the validation layer."
                />

                <MetricCard
                    icon={Activity}
                    label="Activity ↔ Pain"
                    value={
                      correlation.synthetic != null
                          ? Number(correlation.synthetic).toFixed(3)
                          : '—'
                    }
                    description={
                      correlation.source != null
                          ? `Source association: ${Number(correlation.source).toFixed(3)}`
                          : 'Observed statistical association.'
                    }
                />

              </div>
            </div>

            {/* ===================================================== */}
            {/* PRIVACY */}
            {/* ===================================================== */}

            <div className="mt-10">

              <div className="flex items-center gap-3 mb-4">
                <LockKeyhole className="w-5 h-5 text-[#2F6B3F]" />

                <div>
                  <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
                    Privacy Evidence
                  </h3>

                  <p className="text-xs text-[var(--color-cocoa-subtext)]">
                    Independent diagnostics used by Synora's Privacy Gate.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

                <MetricCard
                    icon={Fingerprint}
                    label="MIA AUROC"
                    value={
                      miaValue != null
                          ? Number(miaValue).toFixed(3)
                          : '—'
                    }
                    description="Membership-inference attack performance. Near 0.5 indicates near-random attack performance under this threat model."
                    accent="green"
                />

                <MetricCard
                    icon={ShieldCheck}
                    label="k-Anonymity k"
                    value={
                      kValue != null
                          ? kValue
                          : '—'
                    }
                    description="Smallest synthetic quasi-identifier group size observed."
                    accent="green"
                />

                <MetricCard
                    icon={Fingerprint}
                    label="DCR"
                    value={
                      dcr.value != null
                          ? Number(dcr.value).toFixed(3)
                          : '—'
                    }
                    description="Supporting distance-to-closest-record privacy diagnostic."
                    accent="green"
                />

              </div>
            </div>

            {/* ===================================================== */}
            {/* PRIVACY GATE */}
            {/* ===================================================== */}

            <div
                className={`mt-10 rounded-2xl border-2 p-5 sm:p-6 ${
                    isGatePassed
                        ? 'border-[#2F6B3F]/20 bg-[#EAF4EC]/60'
                        : 'border-[#8B263E]/20 bg-[#FFF1E8]'
                }`}
            >

              <div className="flex items-start gap-4">

                <div
                    className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${
                        isGatePassed
                            ? 'bg-[#2F6B3F] text-white'
                            : 'bg-[#8B263E] text-white'
                    }`}
                >
                  {isGatePassed ? (
                      <CheckCircle2 className="w-6 h-6" />
                  ) : (
                      <AlertTriangle className="w-6 h-6" />
                  )}
                </div>

                <div className="flex-1">

                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-base text-[var(--color-cocoa-text)]">
                      Privacy Gate
                    </h3>

                    <span
                        className={`px-2 py-1 rounded-full text-[10px] font-bold ${
                            isGatePassed
                                ? 'bg-[#2F6B3F] text-white'
                                : 'bg-[#8B263E] text-white'
                        }`}
                    >
                    {gate.status ||
                        gate.tier ||
                        (isGatePassed ? 'PASS' : 'BLOCK')}
                  </span>
                  </div>

                  <p className="text-sm text-[var(--color-cocoa-subtext)] mt-2 leading-relaxed">
                    {gate.interpretation ||
                        gate.summary ||
                        (isGatePassed
                            ? 'No configured privacy-review threshold was breached.'
                            : 'The privacy review requires explicit researcher confirmation before export.')}
                  </p>

                  {Array.isArray(gate.reasons) &&
                      gate.reasons.length > 0 && (
                          <div className="mt-3 space-y-1">
                            {gate.reasons.map((reason, index) => (
                                <p
                                    key={index}
                                    className="text-xs text-[#8B263E]"
                                >
                                  • {reason}
                                </p>
                            ))}
                          </div>
                      )}

                </div>
              </div>
            </div>

            {/* ===================================================== */}
            {/* DISCLAIMER */}
            {/* ===================================================== */}

            <div className="mt-8 pt-6 border-t border-[var(--color-border-subtle)]">

              <p className="text-[11px] leading-relaxed text-[var(--color-cocoa-subtext)]">
                {cert.disclaimer ||
                    'For research and testing purposes only. Not clinically validated. Not a formal privacy guarantee — no differential privacy is applied.'}
              </p>

            </div>

          </div>
        </div>

        {/* ========================================================= */}
        {/* EXPORT ACTIONS */}
        {/* ========================================================= */}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Dataset export */}
          <div className="rounded-[28px] bg-white border border-[var(--color-border-subtle)] p-6 shadow-lg">

            <div className="flex items-center gap-3 mb-4">

              <div className="w-11 h-11 rounded-xl bg-[#6B1D2F] text-white flex items-center justify-center">
                <Download className="w-5 h-5" />
              </div>

              <div>
                <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
                  Synthetic Cohort
                </h3>

                <p className="text-xs text-[var(--color-cocoa-subtext)]">
                  CSV + Excel + privacy certificate bundled together.
                </p>
              </div>

            </div>

            <button
                onClick={handleExport}
                disabled={!isGatePassed || exporting}
                className={`w-full py-4 rounded-2xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                    isGatePassed && !exporting
                        ? 'bg-[#6B1D2F] hover:bg-[#8B263E] text-white hover:scale-[1.01] shadow-xl'
                        : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
            >
              <Download className="w-4 h-4" />

              {exporting
                  ? 'Preparing certified export...'
                  : 'Download Certified Cohort'}
            </button>

          </div>

          {/* Certificate export */}
          <div className="rounded-[28px] bg-white border border-[var(--color-border-subtle)] p-6 shadow-lg">

            <div className="flex items-center gap-3 mb-4">

              <div className="w-11 h-11 rounded-xl bg-[#2F6B3F] text-white flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>

              <div>
                <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
                  Certificate Artifact
                </h3>

                <p className="text-xs text-[var(--color-cocoa-subtext)]">
                  Machine-readable JSON receipt for independent review.
                </p>
              </div>

            </div>

            <div className="flex gap-3">

              <button
                  onClick={handleExportCert}
                  className="flex-1 py-4 rounded-2xl bg-[#2F6B3F] hover:bg-[#255632] text-white font-bold text-sm shadow-lg transition-all hover:scale-[1.01] flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download JSON
              </button>

              <button
                  onClick={copyCertJson}
                  className="px-5 rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] hover:bg-white transition-colors"
                  title="Copy Certificate JSON"
              >
                {copied ? (
                    <CheckCircle2 className="w-5 h-5 text-[#2F6B3F]" />
                ) : (
                    <Copy className="w-5 h-5 text-[var(--color-cocoa-subtext)]" />
                )}
              </button>

            </div>

          </div>

        </div>

        {/* ========================================================= */}
        {/* RAW JSON — COLLAPSED */}
        {/* ========================================================= */}

        <div className="rounded-[28px] bg-white border border-[var(--color-border-subtle)] shadow-lg overflow-hidden">

          <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-[var(--color-cream-surface)] transition-colors"
          >

            <div className="flex items-center gap-3">

              <div className="w-10 h-10 rounded-xl bg-[#140A0C] text-[#E89B72] flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>

              <div>
                <h3 className="font-bold text-sm text-[var(--color-cocoa-text)]">
                  Technical Certificate Data
                </h3>

                <p className="text-xs text-[var(--color-cocoa-subtext)]">
                  View the underlying machine-readable certificate
                </p>
              </div>

            </div>

            {showRawJson ? (
                <ChevronUp className="w-5 h-5 text-[var(--color-cocoa-subtext)]" />
            ) : (
                <ChevronDown className="w-5 h-5 text-[var(--color-cocoa-subtext)]" />
            )}

          </button>

          {showRawJson && (
              <div className="border-t border-[var(--color-border-subtle)] p-5">

                <div className="flex justify-end mb-3">

                  <button
                      onClick={copyCertJson}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--color-cream-surface)] text-xs font-bold text-[var(--color-cocoa-subtext)]"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    {copied ? 'Copied' : 'Copy JSON'}
                  </button>

                </div>

                <pre className="rounded-2xl bg-[#140A0C] text-[#E89B72] p-5 text-xs font-mono max-h-96 overflow-auto leading-relaxed">
              {JSON.stringify(cert, null, 2)}
            </pre>

              </div>
          )}

        </div>

      </div>
  );
}