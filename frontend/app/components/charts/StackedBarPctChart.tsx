// frontend/app/components/charts/GroupedBarChart.tsx
"use client";

import { useEffect, useState } from "react";
import { formatNumber } from "../../lib/utils";

type GroupedBarPoint = {
  label: string;               // "HH:MM" (UTC+7)
  values: Record<string, number>; // { car: 10, motor: 20, ... }
};

type BackendGroupedBarResponse = {
  camera_id: number;
  points: GroupedBarPoint[];
  classes: string[];           // ['car','motor','bus','truck'] (hoặc count_*)
  period?: string;
  timezone?: string;
  message?: string;
  error?: string;
};

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
          `${API_BASE}/api/v1/charts/stacked-bar-pct/${cameraId}`,
          { cache: "no-store" }
        );
        const json = await res.json();

        if (!res.ok) {
          throw new Error(json.message || json.error || `HTTP ${res.status}`);
        }

        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error("GroupedBar fetch error:", err);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được dữ liệu grouped bar"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    const id = setInterval(fetchData, 30000); // 30s

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [cameraId, API_BASE]);

  // --- RENDER STATES ---

  if (loading && !data) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Đang tải grouped bar...
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
        Không có dữ liệu grouped bar
      </div>
    );
  }

  const { points, classes } = data;

  // Tìm max để scale chiều cao cột
  const allValues = points.flatMap((p) =>
    classes.map((cls) => p.values[cls] ?? 0)
  );
  const maxVal = allValues.length ? Math.max(...allValues) : 0;

  if (maxVal === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Tất cả giá trị = 0
      </div>
    );
  }

  // 🔧 Giới hạn số nhãn thời gian để khỏi chồng chữ
  const MAX_LABELS = 12;
  const step = Math.max(1, Math.floor(points.length / MAX_LABELS));

  // Tạo tick cho trục Y (từ max -> 0)
  const yTicks = [1, 0.75, 0.5, 0.25, 0].map((t) =>
    Math.round(maxVal * t)
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Chart với trục X & Y */}
      <div className="flex h-64 rounded-lg border border-slate-700 bg-slate-900/60 p-4">
        {/* Trục Y (bên trái) */}
        <div className="flex w-10 flex-col justify-between border-r border-slate-700 pb-6 pt-2 pr-2 text-[10px] text-slate-400">
          {yTicks.map((v, idx) => (
            <span key={idx}>{formatNumber(v)}</span>
          ))}
        </div>

        {/* Bar + trục X (bên phải) */}
        <div className="ml-3 flex flex-1 flex-col">
          {/* Vùng bar, có thể scroll ngang nếu nhiều điểm */}
          <div className="flex flex-1 items-end gap-3 overflow-x-auto pb-2">
            {points.map((p, idxPoint) => {
              return (
                <div
                  key={idxPoint}
                  className="flex min-w-[40px] flex-1 flex-col items-center gap-1"
                >
                  {/* Nhóm cột theo từng loại xe */}
                  <div className="flex h-40 w-full items-end justify-center gap-1 rounded-md bg-slate-800 px-1 py-1">
                    {classes.map((cls, idxCls) => {
                      const val = p.values[cls] ?? 0;
                      const ratio = val / maxVal;
                      const colorClass = colors[idxCls % colors.length];

                      return (
                        <div
                          key={cls}
                          className="flex flex-1 flex-col items-center"
                        >
                          <div
                            className={`${colorClass} w-full rounded-sm`}
                            style={{ height: `${ratio * 100}%` }}
                            title={`${cls}: ${formatNumber(val)}`}
                          />
                        </div>
                      );
                    })}
                  </div>

                  {/* Label thời gian cho trục X – chỉ hiện một số mốc */}
                  <span className="text-[10px] text-slate-300">
                    {idxPoint % step === 0 ||
                    idxPoint === points.length - 1
                      ? p.label
                      : ""}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Đường baseline cho trục X */}
          <div className="h-px w-full bg-slate-700" />
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {classes.map((cls, idx) => {
          const colorClass = colors[idx % colors.length];
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
