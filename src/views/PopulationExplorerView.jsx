import React, { useState, useEffect } from 'react';
import { FileSpreadsheet, Search, User, ChevronRight, ScatterChart } from 'lucide-react';
import { LineChart as ReLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getPopulationExplorerData } from '../services/mockEngine';
import ScatterPlotChart from '../components/charts/ScatterPlotChart';

export default function PopulationExplorerView() {
  const [data, setData] = useState(null);
  const [selectedPatientId, setSelectedPatientId] = useState('SYN_001');
  const [searchTerm, setSearchTerm] = useState('');
  const [diabeticFilter, setDiabeticFilter] = useState('All');

  useEffect(() => {
    const resData = getPopulationExplorerData();
    setData(resData);
  }, []);

  if (!data) return null;

  const patientRecords = data.records.filter(r => r.patient_id === selectedPatientId);
  const patientInfo = patientRecords[0] || data.patients[0];

  const filteredPatients = (data.patients || []).filter(p => {
    const matchesSearch = p.patient_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDiabetic = diabeticFilter === 'All' || String(p.diabetic) === String(diabeticFilter);
    return matchesSearch && matchesDiabetic;
  });

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-10 animate-fade-in">
      
      {/* Header */}
      <div className="border-b border-[var(--color-border-subtle)] pb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72] text-xs font-bold mb-2">
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span>SYNTHETIC POPULATION ENGINE</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[var(--color-cocoa-text)]">
          Population Explorer &amp; Trajectories
        </h1>
        <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
          Inspect patient-level 6-month longitudinal clinical trajectories and scatter cluster distributions.
        </p>
      </div>

      {/* Multidimensional Scatter Plot Cluster Map */}
      <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-4">
          <div>
            <h3 className="font-serif text-xl font-bold text-[var(--color-cocoa-text)]">
              Multidimensional Population Scatter Distribution
            </h3>
            <p className="text-xs text-[var(--color-cocoa-subtext)] mt-1">
              Age (X) vs. Medication Adherence % (Y) vs. Pain Score (Bubble Radius).
            </p>
          </div>
        </div>
        <ScatterPlotChart data={data.scatterPoints} />
      </div>

      {/* Grid: Patient Selector & Trajectory Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Patient List Selector */}
        <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-lg text-[var(--color-cocoa-text)]">
              Synthetic Patients ({filteredPatients.length})
            </h3>
          </div>

          {/* Search & Filter Controls */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search Patient ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F]"
              />
            </div>

            <select
              value={diabeticFilter}
              onChange={(e) => setDiabeticFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-cream-surface)] focus:ring-2 focus:ring-[#6B1D2F]"
            >
              <option value="All">All Diabetic Conditions</option>
              <option value="1">Diabetic Only</option>
              <option value="0">Non-Diabetic Only</option>
            </select>
          </div>

          {/* Patient Items List */}
          <div className="max-h-[450px] overflow-y-auto space-y-2 pr-1">
            {filteredPatients.map((p) => {
              const isSelected = p.patient_id === selectedPatientId;
              return (
                <button
                  key={p.patient_id}
                  onClick={() => setSelectedPatientId(p.patient_id)}
                  className={`w-full text-left p-3 rounded-xl border text-xs flex items-center justify-between transition-all ${
                    isSelected
                      ? 'bg-[#6B1D2F] text-white border-[#6B1D2F] shadow-md'
                      : 'bg-[var(--color-cream-surface)] text-[var(--color-cocoa-text)] border-[var(--color-border-subtle)] hover:border-[#6B1D2F]'
                  }`}
                >
                  <div>
                    <div className="font-bold flex items-center gap-2">
                      <User className="w-3.5 h-3.5" />
                      <span>{p.patient_id}</span>
                    </div>
                    <div className="text-[10px] opacity-80 mt-0.5">
                      {p.age} yrs • {p.gender} • {p.ethnicity}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 opacity-70" />
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Longitudinal Trajectory Chart & Data Table */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Selected Patient Trajectory Chart */}
          <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 sm:p-8 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-4">
              <div>
                <h3 className="font-serif font-bold text-xl text-[var(--color-cocoa-text)]">
                  Longitudinal Trajectory: {selectedPatientId}
                </h3>
                <p className="text-xs text-[var(--color-cocoa-subtext)]">
                  {patientInfo.age} yrs • {patientInfo.gender} • {patientInfo.ethnicity} • {patientInfo.diabetic === 1 ? 'Diabetic' : 'Non-Diabetic'}
                </p>
              </div>

              <div className="px-3 py-1 rounded-full text-xs font-bold bg-[#6B1D2F]/10 text-[#6B1D2F] dark:text-[#E89B72]">
                6 Months Recorded
              </div>
            </div>

            {/* Recharts 6-Month Trajectory Chart */}
            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ReLineChart data={patientRecords}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis dataKey="month" stroke="var(--color-cocoa-subtext)" fontSize={11} label={{ value: 'Month', position: 'bottom', offset: -5 }} />
                  <YAxis stroke="var(--color-cocoa-subtext)" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--color-card-white)', borderRadius: '12px', border: '1px solid var(--color-border-subtle)' }} />
                  <Line type="monotone" dataKey="activity_score" stroke="#2F6B3F" strokeWidth={2} name="Activity Score" />
                  <Line type="monotone" dataKey="pain_score" stroke="#B83B3B" strokeWidth={2} name="Pain Score" />
                  <Line type="monotone" dataKey="hba1c" stroke="#6B1D2F" strokeWidth={2} name="HbA1c (%)" />
                </ReLineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Monthly Records Table */}
          <div className="rounded-[28px] bg-[var(--color-card-white)] p-6 shadow-xl border border-[var(--color-border-subtle)] space-y-4">
            <h3 className="font-serif font-bold text-lg text-[var(--color-cocoa-text)]">
              6-Month Records Table for {selectedPatientId}
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[var(--color-border-subtle)] text-[var(--color-cocoa-subtext)] uppercase font-semibold text-[10px]">
                    <th className="py-2.5 px-3">Month</th>
                    <th className="py-2.5 px-3">HbA1c (%)</th>
                    <th className="py-2.5 px-3">Systolic BP</th>
                    <th className="py-2.5 px-3">Activity Score</th>
                    <th className="py-2.5 px-3">Pain Score</th>
                    <th className="py-2.5 px-3">Adherence (%)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border-subtle)] font-mono">
                  {patientRecords.map((r) => (
                    <tr key={r.month} className="hover:bg-[var(--color-cream-surface)] transition-colors">
                      <td className="py-2.5 px-3 font-bold font-sans">Month {r.month}</td>
                      <td className="py-2.5 px-3 text-[#6B1D2F] dark:text-[#E89B72]">{r.hba1c}</td>
                      <td className="py-2.5 px-3">{r.systolic_bp} mmHg</td>
                      <td className="py-2.5 px-3 text-[#2F6B3F] font-bold">{r.activity_score}</td>
                      <td className="py-2.5 px-3 text-[#B83B3B] font-bold">{r.pain_score}</td>
                      <td className="py-2.5 px-3">{r.medication_adherence}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
