"use client";

import { useEffect, useState } from "react";
import { formatNumber } from "../../lib/utils";

interface GroupedBarPoint {
  label: string; // HH:MM
  values: Record<string, number>; // { car: 10, motor: 20, ... }
}

interface BackendGroupedBarResponse {
  camera_id: number;
  points: GroupedBarPoint[];
  classes: string[];
  period?: string;
  timezone?: string;
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

type Props = {
  cameraId: number;
};

export default function GroupedBarChart({ cameraId }: Props) {
  const [data, setData] = useState<BackendGroupedBarResponse | null>(null);
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
          `${API_BASE}/api/v1/charts/grouped-bar/${cameraId}`,
          { cache: "no-store" },
        );
        const json = await res.json();

        if (!res.ok) {
          throw new Error(json.message || json.error || `HTTP ${res.status}`);
        }
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error("GroupedBarChart fetch error:", err);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được dữ liệu grouped-bar",
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
        Đang tải grouped-bar...
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

  return (
    <div className="flex flex-col gap-4">
      {/* Chart */}
      <div className="flex h-64 items-end gap-3 overflow-x-auto rounded-lg border border-slate-700 bg-slate-900/40 p-4">
        {points.map((point, pointIndex) => (
          <div
            key={pointIndex}
            className="flex min-w-[48px] flex-1 flex-col items-center gap-2"
          >
            {/* Cột bars */}
            <div className="flex h-40 w-full items-end justify-center gap-1">
              {classes.map((cls, classIndex) => {
                const val = point.values[cls] ?? 0;
                const heightPct = maxValue > 0 ? (val / maxValue) * 100 : 0;
                const colorClass = colors[classIndex % colors.length];

                return (
                  <div
                    key={cls}
                    className="flex flex-col items-center"
                    title={`${cls.toUpperCase()}: ${val}`}
                  >
                    <span className="mb-1 text-[10px] text-slate-300">
                      {val > 0 ? formatNumber(val) : ""}
                    </span>
                    <div className="flex h-32 w-3 items-end rounded-full bg-slate-800">
                      <div
                        className={`w-full rounded-full ${colorClass} transition-all duration-300 hover:opacity-80`}
                        style={{ height: `${heightPct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-1 text-[11px] text-slate-300">
              {point.label}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {classes.map((cls, index) => {
          const colorClass = colors[index % colors.length];
          return (
            <div
              key={cls}
              className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-2 py-1"
            >
              <span className={`h-3 w-3 rounded-full ${colorClass}`} />
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
