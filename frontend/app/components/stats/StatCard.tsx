"use client";

import React from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  helperText?: string;
  trend?: number; // Optional: Để hiển thị % tăng giảm nếu muốn
}

export default function StatCard({ label, value, helperText, trend }: StatCardProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 shadow-sm transition-all hover:border-slate-700">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
        {label}
      </p>
      
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-white tracking-tight">
          {value}
        </span>
        {trend !== undefined && (
          <span className={`text-xs font-medium ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>

      {helperText && (
        <p className="mt-1 text-[10px] text-slate-500">
          {helperText}
        </p>
      )}
    </div>
  );
}