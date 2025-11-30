"use client";

import { useEffect, useState } from "react";
import { formatNumber } from "../../lib/utils";

interface AreaPoint {
  label: string; // "HH:MM"
  values: Record<string, number>;
}

interface BackendAreaResponse {
  camera_id: number;
  points: AreaPoint[];
  classes: string[];
  period?: string;
  timezone?: string;
  chart_type?: string;
  message?: string;
}

const colors = [
  "bg-emerald-400",
  "bg-sky-400",
  "bg-amber-400",
  "bg-violet-400",
  "bg-rose-400",
  "bg-indigo-400",
];

const colorHex: Record<string, string> = {
  "bg-emerald-400": "#34d399",
  "bg-sky-400": "#38bdf8",
  "bg-amber-400": "#fbbf24",
  "bg-violet-400": "#a78bfa",
  "bg-rose-400": "#fb7185",
  "bg-indigo-400": "#818cf8",
};

type Props = {
  cameraId: number;
};

export default function AreaChart({ cameraId }: Props) {
  const [data, setData] = useState<BackendAreaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(
          `${API_BASE}/api/v1/charts/area/${cameraId}`,
          { cache: "no-store" },
        );
        const json = await res.json();
        if (!res.ok) {
          throw new Error(json.message || json.error || `HTTP ${res.status}`);
        }
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error("AreaChart fetch error:", err);
          setError(
            err instanceof Error ? err.message : "Không lấy được dữ liệu area",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    const id = setInterval(fetchData, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [cameraId, API_BASE]);

  if (loading && !data) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Đang tải area chart...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center text-yellow-400">
        ⚠️ {error}
      </div>
    );
  }

  if (!data || !data.points.length || !data.classes.length) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Không có dữ liệu
      </div>
    );
  }

  const { points, classes } = data;

  const allValues = points.flatMap((p) =>
    classes.map((cls) => p.values[cls] ?? 0),
  );
  const maxValue = allValues.length ? Math.max(...allValues) : 0;

  if (maxValue === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Tất cả giá trị = 0
      </div>
    );
  }

  const width = 320;
  const height = 180;
  const paddingX = 24;
  const paddingY = 16;
  const innerWidth = width - paddingX * 2;
  const innerHeight = height - paddingY * 2;
  const n = points.length;

  const getX = (idx: number) =>
    paddingX +
    (n === 1 ? innerWidth / 2 : (idx / (n - 1)) * innerWidth);
  const getY = (v: number) =>
    paddingY + (1 - v / maxValue) * innerHeight;

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-900/60 p-3">
        <svg width={width} height={height}>
          <line
            x1={paddingX}
            y1={paddingY + innerHeight}
            x2={paddingX + innerWidth}
            y2={paddingY + innerHeight}
            stroke="#1f2937"
            strokeWidth={1}
          />

          {classes.map((cls, idxCls) => {
            const colorClass = colors[idxCls % colors.length];
            const stroke = colorHex[colorClass] || "#38bdf8";

            const seriesValues = points.map((p) => p.values[cls] ?? 0);

            const pathPoints = seriesValues
              .map((v, i) => `${getX(i)},${getY(v)}`)
              .join(" ");

            const polygonPoints =
              pathPoints +
              ` ${getX(n - 1)},${paddingY + innerHeight}` +
              ` ${getX(0)},${paddingY + innerHeight}`;

            return (
              <g key={cls}>
                <polygon
                  points={polygonPoints}
                  fill={stroke}
                  fillOpacity={0.15}
                  stroke="none"
                />
                <polyline
                  points={pathPoints}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              </g>
            );
          })}

          {points.map((p, idx) => (
            <text
              key={idx}
              x={getX(idx)}
              y={height - 4}
              textAnchor="middle"
              className="fill-slate-400 text-[10px]"
            >
              {p.label}
            </text>
          ))}
        </svg>
      </div>

      <div className="flex flex-wrap gap-3">
        {classes.map((cls, idx) => {
          const colorClass = colors[idx % colors.length];
          return (
            <div
              key={cls}
              className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-2 py-1"
            >
              <span className={`h-3 w-3 rounded-sm ${colorClass}`} />
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-200">
                {cls}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
