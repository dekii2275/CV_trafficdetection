"use client";

import { useEffect, useState } from "react";
import { formatNumber } from "../../lib/utils";

interface BoxplotItem {
  name: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
}

interface BackendBoxplotResponse {
  camera_id: number;
  items: BoxplotItem[];
  classes?: string[];
  message?: string;
}

type Props = {
  cameraId: number;
};

export default function BoxplotChart({ cameraId }: Props) {
  const [data, setData] = useState<BackendBoxplotResponse | null>(null);
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
          `${API_BASE}/api/v1/charts/boxplot/${cameraId}`,
          { cache: "no-store" },
        );
        const json = await res.json();
        if (!res.ok) {
          throw new Error(json.message || json.error || `HTTP ${res.status}`);
        }
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error("BoxplotChart fetch error:", err);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được dữ liệu boxplot",
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
        Đang tải boxplot...
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

  if (!data || !data.items.length) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Không có dữ liệu
      </div>
    );
  }

  const items = data.items;

  const allValues = items.flatMap((i) => [
    i.min,
    i.q1,
    i.median,
    i.q3,
    i.max,
  ]);
  const globalMin = Math.min(...allValues);
  const globalMax = Math.max(...allValues);
  const range = globalMax - globalMin || 1;

  const width = Math.max(260, items.length * 60);
  const height = 200;
  const paddingX = 30;
  const paddingY = 20;
  const innerHeight = height - paddingY * 2;
  const innerWidth = width - paddingX * 2;

  const getX = (idx: number) =>
    paddingX +
    (items.length === 1 ? innerWidth / 2 : (idx / (items.length - 1)) * innerWidth);
  const getY = (v: number) =>
    paddingY + (1 - (v - globalMin) / range) * innerHeight;

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

          {items.map((item, idx) => {
            const cx = getX(idx);
            const yMin = getY(item.min);
            const yQ1 = getY(item.q1);
            const yMed = getY(item.median);
            const yQ3 = getY(item.q3);
            const yMax = getY(item.max);

            return (
              <g key={item.name}>
                <line
                  x1={cx}
                  y1={yMin}
                  x2={cx}
                  y2={yMax}
                  stroke="#e5e7eb"
                  strokeWidth={1}
                />
                <line
                  x1={cx - 10}
                  y1={yMin}
                  x2={cx + 10}
                  y2={yMin}
                  stroke="#e5e7eb"
                  strokeWidth={1}
                />
                <line
                  x1={cx - 10}
                  y1={yMax}
                  x2={cx + 10}
                  y2={yMax}
                  stroke="#e5e7eb"
                  strokeWidth={1}
                />
                <rect
                  x={cx - 14}
                  y={yQ3}
                  width={28}
                  height={Math.max(4, yQ1 - yQ3)}
                  fill="#0f172a"
                  stroke="#38bdf8"
                  strokeWidth={1.5}
                  rx={4}
                />
                <line
                  x1={cx - 14}
                  y1={yMed}
                  x2={cx + 14}
                  y2={yMed}
                  stroke="#fbbf24"
                  strokeWidth={2}
                />
                <text
                  x={cx}
                  y={height - 4}
                  textAnchor="middle"
                  className="fill-slate-300 text-[10px]"
                >
                  {item.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
        <div>Min: {formatNumber(globalMin)}</div>
        <div>Max: {formatNumber(globalMax)}</div>
      </div>
    </div>
  );
}
