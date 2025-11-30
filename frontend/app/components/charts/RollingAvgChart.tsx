"use client";

import { useEffect, useState } from "react";
import { formatNumber } from "../../lib/utils";

interface RollingPoint {
  label: string; // HH:MM
  values: Record<string, number>; // { car: 10, motor: 20, ... }
}

interface BackendRollingResponse {
  camera_id: number;
  points: RollingPoint[];
  classes: string[];
  window: number;
  period?: string;
  timezone?: string;
  message?: string;
  error?: string;
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

export default function RollingAvgChart({ cameraId }: Props) {
  const [data, setData] = useState<BackendRollingResponse | null>(null);
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
          `${API_BASE}/api/v1/charts/rolling-avg/${cameraId}`,
          { cache: "no-store" }
        );
        const json = await res.json();

        if (!res.ok) {
          throw new Error(json.message || json.error || `HTTP ${res.status}`);
        }

        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error("RollingAvgChart fetch error:", err);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được dữ liệu rolling avg"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    const id = setInterval(fetchData, 30000); // refresh mỗi 30s

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [cameraId, API_BASE]);

  if (loading && !data) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Đang tải rolling average...
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
        Không có dữ liệu rolling avg
      </div>
    );
  }

  const { points, classes } = data;

  const allValues = points.flatMap((p) =>
    classes.map((cls) => p.values[cls] ?? 0)
  );
  const maxValue = Math.max(...allValues, 0);

  if (maxValue === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Tất cả giá trị = 0
      </div>
    );
  }

  // =============== CẤU HÌNH SVG + SCROLL NGANG ===============
  const height = 220;
  const paddingLeft = 48; // chừa chỗ cho trục Y + số
  const paddingRight = 16;
  const paddingTop = 16;
  const paddingBottom = 28; // chừa chỗ cho label X

  const minPerPointWidth = 40; // mỗi điểm trên trục X chiếm ~40px
  const innerBaseWidth = 320;
  const innerWidth = Math.max(points.length * minPerPointWidth, innerBaseWidth);

  const width = paddingLeft + innerWidth + paddingRight;
  const innerHeight = height - paddingTop - paddingBottom;
  const n = points.length;

  const getX = (idx: number) =>
    paddingLeft + (n === 1 ? innerWidth / 2 : (idx / (n - 1)) * innerWidth);

  const getY = (v: number) =>
    paddingTop + (1 - v / maxValue) * innerHeight;

  // =============== TICK TRỤC Y ===============
  const yTicks = 4; // số vạch (không tính 0)
  const tickValues = Array.from({ length: yTicks + 1 }, (_, i) =>
    (maxValue / yTicks) * i
  );

  return (
    <div className="flex flex-col gap-4">
      {/* SVG có scroll ngang */}
      <div className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-900/60 p-3">
        <svg width={width} height={height}>
          {/* Grid ngang + tick Y */}
          {tickValues.map((v, idx) => {
            const y = getY(v);
            const isZero = v === 0;

            return (
              <g key={idx}>
                {/* line ngang */}
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={paddingLeft + innerWidth}
                  y2={y}
                  stroke={isZero ? "#4b5563" : "#1f2937"}
                  strokeWidth={isZero ? 1.2 : 1}
                  strokeDasharray={isZero ? "0" : "4 4"}
                />
                {/* số trục Y */}
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

          {/* Đường rolling-avg cho từng class */}
          {classes.map((cls, idxCls) => {
            const colorClass = colors[idxCls % colors.length];
            const stroke = colorHex[colorClass] || "#38bdf8";

            const path = points
              .map((p, i) => {
                const v = p.values[cls] ?? 0;
                return `${getX(i)},${getY(v)}`;
              })
              .join(" ");

            return (
              <polyline
                key={cls}
                points={path}
                fill="none"
                stroke={stroke}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
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

      {/* Info + legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
        <span>Cửa sổ làm mượt: {data.window}</span>
        {classes.map((cls, idx) => {
          const colorClass = colors[idx % colors.length];
          return (
            <span
              key={cls}
              className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-800/60 px-2 py-1"
            >
              <span className={`h-3 w-3 rounded-full ${colorClass}`} />
              <span className="uppercase tracking-wide text-slate-200">
                {cls}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}
