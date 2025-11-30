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

  // ==== cấu hình SVG giống RollingAvg: có trục Y + scroll ngang ====
  const height = 220;
  const paddingLeft = 48; // chừa chỗ cho số trục Y
  const paddingRight = 16;
  const paddingTop = 16;
  const paddingBottom = 28; // chừa chỗ cho label X

  const minPerPointWidth = 40;
  const innerBaseWidth = 320;
  const innerWidth = Math.max(points.length * minPerPointWidth, innerBaseWidth);

  const width = paddingLeft + innerWidth + paddingRight;
  const innerHeight = height - paddingTop - paddingBottom;
  const n = points.length;

  const getX = (idx: number) =>
    paddingLeft + (n === 1 ? innerWidth / 2 : (idx / (n - 1)) * innerWidth);
  const getY = (v: number) =>
    paddingTop + (1 - v / maxValue) * innerHeight;

  // trục Y – tick
  const yTicks = 4;
  const tickValues = Array.from({ length: yTicks + 1 }, (_, i) =>
    (maxValue / yTicks) * i,
  );

  const path = points
    .map((p, i) => `${getX(i)},${getY(p.value)}`)
    .join(" ");

  return (
    <div className="flex flex-col gap-4">
      {/* SVG có thể cuộn ngang */}
      <div className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-900/60 p-3">
        <svg width={width} height={height}>
          {/* Grid ngang + tick Y */}
          {tickValues.map((v, idx) => {
            const y = getY(v);
            const isZero = v === 0;

            return (
              <g key={idx}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={paddingLeft + innerWidth}
                  y2={y}
                  stroke={isZero ? "#4b5563" : "#1f2937"}
                  strokeWidth={isZero ? 1.2 : 1}
                  strokeDasharray={isZero ? "0" : "4 4"}
                />
                <text
                  x={paddingLeft - 8}
                  y={y + 3}
                  textAnchor="end"
                  className="fill-slate-400 text-[10px]"
                >
                  {formatNumber(Math.round(v))}
                </text>
              </g>
            );
          })}

          {/* Trục Y */}
          <line
            x1={paddingLeft}
            y1={paddingTop}
            x2={paddingLeft}
            y2={paddingTop + innerHeight}
            stroke="#4b5563"
            strokeWidth={1.2}
          />

          {/* Trục X */}
          <line
            x1={paddingLeft}
            y1={paddingTop + innerHeight}
            x2={paddingLeft + innerWidth}
            y2={paddingTop + innerHeight}
            stroke="#4b5563"
            strokeWidth={1.2}
          />

          {/* Đường flow tổng */}
          <polyline
            points={path}
            fill="none"
            stroke="#38bdf8"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Điểm + peak */}
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

          {/* Label trục X */}
          {points.map((p, idx) => (
            <text
              key={idx}
              x={getX(idx)}
              y={height - 8}
              textAnchor="middle"
              className="fill-slate-400 text-[10px]"
            >
              {p.label}
            </text>
          ))}
        </svg>
      </div>

      {/* Legend */}
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
