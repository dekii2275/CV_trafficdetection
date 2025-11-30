"use client";

import { useEffect, useState } from "react";
import { formatNumber } from "../../lib/utils";

interface PeakPoint {
  label: string;
  value: number;
  is_peak: boolean;
  timestamp: string;
}

interface BackendPeaksResponse {
  camera_id: number;
  points: PeakPoint[];
  peaks: { label: string; value: number; timestamp: string }[];
  period?: string;
  timezone?: string;
  message?: string;
}

type Props = {
  cameraId: number;
};

export default function PeaksChart({ cameraId }: Props) {
  const [data, setData] = useState<BackendPeaksResponse | null>(null);
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
          `${API_BASE}/api/v1/charts/peaks/${cameraId}`,
          { cache: "no-store" },
        );
        const json = await res.json();
        if (!res.ok) {
          throw new Error(json.message || json.error || `HTTP ${res.status}`);
        }
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error("PeaksChart fetch error:", err);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được dữ liệu peaks",
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
        Đang tải peak chart...
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

  if (!data || !data.points.length) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Không có dữ liệu
      </div>
    );
  }

  const points = data.points;

  const maxValue = Math.max(...points.map((p) => p.value), 0);
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

  const path = points
    .map((p, i) => `${getX(i)},${getY(p.value)}`)
    .join(" ");

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

          <polyline
            points={path}
            fill="none"
            stroke="#38bdf8"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {points.map((p, idx) => {
            const x = getX(idx);
            const y = getY(p.value);
            if (!p.is_peak) {
              return (
                <circle
                  key={idx}
                  cx={x}
                  cy={y}
                  r={3}
                  fill="#64748b"
                />
              );
            }

            return (
              <g key={idx}>
                <circle
                  cx={x}
                  cy={y}
                  r={4}
                  fill="#f97316"
                  stroke="#fed7aa"
                  strokeWidth={1.5}
                />
                <title>
                  {p.label} • {formatNumber(p.value)} (peak)
                </title>
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

      <div className="flex items-center gap-4 text-xs text-slate-400">
        <div className="flex items-center gap-1">
          <span className="h-[6px] w-6 rounded-full bg-sky-400" />
          <span>Flow tổng</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-full bg-orange-400" />
          <span>Đỉnh (peak)</span>
        </div>
      </div>
    </div>
  );
}
