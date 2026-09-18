import React from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DemographicsChart({ ageData, genderData }) {
  const COLORS = ['#6B1D2F', '#2F6B3F', '#C68B2C', '#8B263E'];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      
      {/* Age Histogram */}
      <div className="rounded-2xl bg-[var(--color-cream-surface)] p-4 border border-[var(--color-border-subtle)] space-y-2">
        <h4 className="text-xs font-bold font-serif text-[var(--color-cocoa-text)]">Age Bracket Frequencies</h4>
        <div className="h-52 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ageData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="range" stroke="var(--color-cocoa-subtext)" fontSize={11} />
              <YAxis stroke="var(--color-cocoa-subtext)" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--color-card-white)', borderRadius: '12px', border: '1px solid var(--color-border-subtle)' }} />
              <Bar dataKey="count" fill="#6B1D2F" radius={[8, 8, 0, 0]} name="Patients" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Gender Distribution Doughnut */}
      <div className="rounded-2xl bg-[var(--color-cream-surface)] p-4 border border-[var(--color-border-subtle)] space-y-2">
        <h4 className="text-xs font-bold font-serif text-[var(--color-cocoa-text)]">Gender Distribution Doughnut</h4>
        <div className="h-52 w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={genderData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={75}
                paddingAngle={4}
                dataKey="value"
                nameKey="name"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {genderData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: 'var(--color-card-white)', borderRadius: '12px', border: '1px solid var(--color-border-subtle)' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}
