import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function ScatterPlotChart({ data }) {
  const diabeticPoints = data.filter(p => p.diabetic === 1);
  const nonDiabeticPoints = data.filter(p => p.diabetic === 0);

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis type="number" dataKey="age" name="Age" unit=" yrs" stroke="var(--color-cocoa-subtext)" fontSize={11} />
          <YAxis type="number" dataKey="adherence" name="Adherence" unit="%" stroke="var(--color-cocoa-subtext)" fontSize={11} />
          <ZAxis type="number" dataKey="painScore" range={[40, 200]} name="Pain Score" />
          <Tooltip 
            cursor={{ strokeDasharray: '3 3' }}
            contentStyle={{ backgroundColor: 'var(--color-card-white)', borderRadius: '12px', border: '1px solid var(--color-border-subtle)', fontSize: '12px' }}
          />
          <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px', fontWeight: 'bold' }} />
          <Scatter name="Diabetic Patients" data={diabeticPoints} fill="#6B1D2F" />
          <Scatter name="Non-Diabetic Patients" data={nonDiabeticPoints} fill="#2F6B3F" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
