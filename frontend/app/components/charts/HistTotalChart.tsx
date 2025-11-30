"use client";

import { useEffect, useState } from "react";
import { formatNumber } from "../../lib/utils";

interface HistPoint {
  label: string;
  value: number;
}

interface BackendHistResponse {
  camera_id: number;
  points: HistPoint[];
  bins?: number;
  metric?: string;
  message?: string;
}

type Props = {
  cameraId: number;
};

export default function HistTotalChart({ cameraId }: Props) {
  const [data, setData] = useState<BackendHistResponse | null>(null);
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
          `${API_BASE}/api/v1/charts/hist-total/${cameraId}`,
          { cache: "no-store" },
        );
        const json = await res.json();
        if (!res.ok) {
          throw new Error(json.message || json.error || `HTTP ${res.status}`);
        }
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error("HistTotalChart fetch error:", err);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được dữ liệu histogram",
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
        Đang tải histogram...
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
  const maxCount = Math.max(...points.map((p) => p.value));

  if (maxCount === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        Tất cả count = 0
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex h-64 items-end gap-2 overflow-x-auto rounded-lg border border-slate-700 bg-slate-900/60 p-4">
        {points.map((p, idx) => {
          const heightPct = (p.value / maxCount) * 100;
          return (
            <div
              key={idx}
              className="flex min-w-[24px] flex-1 flex-col items-center gap-1"
            >
              <span className="text-[10px] text-slate-300">
                {p.value > 0 ? formatNumber(p.value) : ""}
              </span>
              <div className="flex h-40 w-full items-end rounded bg-slate-800">
                <div
                  className="w-full rounded bg-sky-400 transition-all duration-300 hover:opacity-80"
                  style={{ height: `${heightPct}%` }}
                />
              </div>
              <span className="mt-1 text-[10px] text-slate-400">
                {p.label}
              </span>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-slate-400">
        Mỗi cột tương ứng một khoảng (bin) giá trị tổng phương tiện.
      </p>
    </div>
  );
}
