"use client";

import type { ChartPoint } from "../../lib/types";
import { formatNumber } from "../../lib/utils";

interface BarChartProps {
  points: ChartPoint[];
  title?: string;
}

export default function BarChart({ points, title }: BarChartProps) {
  if (points.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        <p>Không có dữ liệu</p>
      </div>
    );
  }

  const maxValue = Math.max(...points.map((point) => point.value), 1);

  return (
    <div className="space-y-4">
      {title && (
        <h4 className="text-sm font-semibold text-slate-300">{title}</h4>
      )}
      <div className="flex h-64 items-end gap-2 rounded-lg bg-slate-900 p-4">
        {points.map((point, index) => {
          const height = maxValue === 0 ? 0 : (point.value / maxValue) * 100;
          const hasValue = point.value > 0;

          return (
            <div
              key={point.label}
              className="group flex flex-1 flex-col items-center gap-2"
            >
              {/* Bar */}
              <div className="relative flex w-full items-end justify-center">
                <div
                  className={`w-full rounded-t transition-all duration-300 ${
                    hasValue
                      ? "bg-gradient-to-t from-emerald-500 to-emerald-400 group-hover:from-emerald-400 group-hover:to-emerald-300"
                      : "bg-slate-700"
                  }`}
                  style={{
                    height: `${Math.max(height, hasValue ? 5 : 0)}%`,
                    minHeight: hasValue ? "4px" : "0",
                  }}
                />
                {/* Value label on hover */}
                {hasValue && (
                  <div className="absolute -top-8 hidden rounded bg-slate-800 px-2 py-1 text-xs text-white shadow-lg group-hover:block">
                    {formatNumber(point.value)}
                  </div>
                )}
              </div>
              {/* X-axis label */}
              <span className="text-xs text-slate-400">{point.label}</span>
            </div>
          );
        })}
      </div>
      {/* Summary */}
      <div className="flex justify-between text-xs text-slate-400">
        <span>Tổng: {formatNumber(points.reduce((sum, p) => sum + p.value, 0))}</span>
        <span>Max: {formatNumber(maxValue)}</span>
      </div>
    </div>
  );
}

