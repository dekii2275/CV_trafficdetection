"use client";

import { formatNumber, calculatePercentage } from "../../lib/utils";

interface PieChartProps {
  data: Array<{ label: string; value: number }>;
}

const colors = [
  "bg-emerald-400",
  "bg-sky-400",
  "bg-amber-400",
  "bg-violet-400",
  "bg-rose-400",
  "bg-indigo-400",
];

const colorHover = [
  "bg-emerald-300",
  "bg-sky-300",
  "bg-amber-300",
  "bg-violet-300",
  "bg-rose-300",
  "bg-indigo-300",
];

export default function PieChart({ data }: PieChartProps) {
  const total = data.reduce((sum, item) => sum + item.value, 0);

  if (total === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        <p>Không có dữ liệu</p>
      </div>
    );
  }

  // Tính góc cho mỗi phần
  let currentAngle = -90; // Bắt đầu từ trên cùng
  const segments = data
    .filter((item) => item.value > 0)
    .map((item, index) => {
      const percent = calculatePercentage(item.value, total);
      const angle = (percent / 100) * 360;
      const startAngle = currentAngle;
      currentAngle += angle;

      return {
        ...item,
        percent,
        startAngle,
        angle,
        color: colors[index % colors.length],
        colorHover: colorHover[index % colorHover.length],
      };
    });

  // Tính vị trí cho label
  const radius = 80;
  const centerX = 100;
  const centerY = 100;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Pie Chart SVG */}
      <div className="relative">
        <svg width="200" height="200" viewBox="0 0 200 200" className="transform -rotate-90">
          {segments.map((segment, index) => {
            const startAngleRad = (segment.startAngle * Math.PI) / 180;
            const endAngleRad = ((segment.startAngle + segment.angle) * Math.PI) / 180;

            const x1 = centerX + radius * Math.cos(startAngleRad);
            const y1 = centerY + radius * Math.sin(startAngleRad);
            const x2 = centerX + radius * Math.cos(endAngleRad);
            const y2 = centerY + radius * Math.sin(endAngleRad);

            const largeArcFlag = segment.angle > 180 ? 1 : 0;

            const pathData = [
              `M ${centerX} ${centerY}`,
              `L ${x1} ${y1}`,
              `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
              "Z",
            ].join(" ");

            // Map colors to actual hex values
            const colorMap: Record<string, string> = {
              "bg-emerald-400": "#34d399",
              "bg-sky-400": "#38bdf8",
              "bg-amber-400": "#fbbf24",
              "bg-violet-400": "#a78bfa",
              "bg-rose-400": "#fb7185",
              "bg-indigo-400": "#818cf8",
            };

            return (
              <path
                key={index}
                d={pathData}
                fill={colorMap[segment.color] || "#34d399"}
                className="transition-all duration-300 hover:opacity-80"
              />
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="grid w-full grid-cols-2 gap-3">
        {segments.map((segment, index) => (
          <div
            key={index}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/50 p-2"
          >
            <div className={`h-4 w-4 rounded-full ${segment.color}`} />
            <div className="flex-1">
              <div className="text-sm font-semibold text-white">{segment.label}</div>
              <div className="text-xs text-slate-400">
                {formatNumber(segment.value)} · {segment.percent.toFixed(1)}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

