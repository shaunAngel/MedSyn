import React from 'react';

export default function CorrelationHeatmap({ matrix }) {
  if (!matrix) return null;

  const features = ['HbA1c', 'SystolicBP', 'ActivityScore', 'PainScore', 'Adherence'];

  const getColor = (val) => {
    if (val === 1.0) return 'bg-[#6B1D2F] text-white font-bold';
    if (val <= -0.5) return 'bg-[#6B1D2F]/90 text-white font-bold shadow-sm';
    if (val < 0) return 'bg-[#6B1D2F]/20 text-[#6B1D2F] dark:text-[#E89B72] font-semibold';
    if (val >= 0.4) return 'bg-[#2F6B3F]/20 text-[#2F6B3F] font-semibold';
    return 'bg-[var(--color-cream-surface)] text-[var(--color-cocoa-text)]';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-center text-xs border-collapse">
        <thead>
          <tr className="border-b border-[var(--color-border-subtle)] text-[var(--color-cocoa-subtext)] uppercase font-semibold text-[10px]">
            <th className="py-2.5 px-3 text-left">Feature</th>
            {features.map(f => (
              <th key={f} className="py-2.5 px-3">{f}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border-subtle)] font-mono">
          {matrix.map(row => (
            <tr key={row.feature} className="hover:bg-[var(--color-cream-surface)]/50 transition-colors">
              <td className="py-3 px-3 text-left font-bold font-sans text-[var(--color-cocoa-text)]">{row.feature}</td>
              {features.map(f => {
                const val = row[f];
                return (
                  <td key={f} className="py-2.5 px-2">
                    <span className={`inline-block w-full py-1.5 px-2 rounded-xl text-[11px] ${getColor(val)}`}>
                      {val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
