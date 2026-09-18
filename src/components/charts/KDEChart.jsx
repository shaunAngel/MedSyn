import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function KDEChart({ data }) {
  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="sourceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6B1D2F" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#6B1D2F" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="syntheticGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2F6B3F" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#2F6B3F" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} stroke="var(--color-border-subtle)" />
          <XAxis 
            dataKey="hba1c" 
            stroke="var(--color-cocoa-subtext)" 
            fontSize={11} 
            tickLine={false} 
            label={{ value: 'HbA1c Level (%)', position: 'bottom', offset: -5, fill: 'var(--color-cocoa-subtext)', fontSize: 11 }}
          />
          <YAxis stroke="var(--color-cocoa-subtext)" fontSize={11} tickLine={false} />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'var(--color-card-white)', 
              borderRadius: '16px', 
              border: '1px solid var(--color-border-subtle)',
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
              fontSize: '12px'
            }} 
          />
          <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px', fontWeight: 'bold' }} />
          <Area 
            type="monotone" 
            dataKey="SourceDensity" 
            stroke="#6B1D2F" 
            fill="url(#sourceGradient)" 
            strokeWidth={3} 
            name="Source Evidence Density" 
          />
          <Area 
            type="monotone" 
            dataKey="SyntheticDensity" 
            stroke="#2F6B3F" 
            fill="url(#syntheticGradient)" 
            strokeWidth={3} 
            name="Synthetic Copula Density" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
