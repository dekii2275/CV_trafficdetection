"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import StatCard from "./StatCard";
import { formatCompactNumber, formatNumber } from "../../lib/utils";

type BackendStats = {
  timestemp: string;
  car: number;
  mortor: number;      // xe máy / bike
  bus: number;
  truck: number;
  total_vehicles: number;
};

type RealtimeStatsProps = {
  cameraId: number;
  cameraLabel?: string;   // ví dụ: "Camera 1 - Cổng chính"
};

export default function RealtimeStats({
  cameraId,
  cameraLabel,
}: RealtimeStatsProps) {
  const [stats, setStats] = useState<BackendStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const API_BASE =
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

    async function fetchStats() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/stats/${cameraId}`, {
          cache: "no-store",
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = (await res.json()) as BackendStats;
        if (!cancelled) {
          setStats(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Fetch stats error:", err);
          setError("Không lấy được dữ liệu realtime");
        }
      }
    }

    fetchStats();
    const interval = setInterval(fetchStats, 5000); // 5s cập nhật 1 lần

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [cameraId]);

  const total = stats?.total_vehicles ?? 0;
  const car = stats?.car ?? 0;
  const truck = stats?.truck ?? 0;
  const bike = stats?.mortor ?? 0;
  const bus = stats?.bus ?? 0;

  const summaryCards = [
    {
      label: "Tổng lượt hôm nay",
      value: formatNumber(total),
      helperText: "Tính từ 00:00",
      trend: undefined as number | undefined,
    },
  ];

  const breakdownCards = [
    {
      label: "Lượt CAR",
      value: formatCompactNumber(car),
      helperText: "Từ đầu ngày",
    },
    {
      label: "Lượt TRUCK",
      value: formatCompactNumber(truck),
      helperText: "Từ đầu ngày",
    },
    {
      label: "Lượt BIKE",
      value: formatCompactNumber(bike),
      helperText: "Từ đầu ngày",
    },
    {
      label: "Lượt BUS",
      value: formatCompactNumber(bus),
      helperText: "Từ đầu ngày",
    },
  ];

  return (
    <Card>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">
            Realtime Vehicle Count{" "}
            {cameraLabel ? `• ${cameraLabel}` : `• Camera ${cameraId}`}
          </h2>
          <p className="text-sm text-slate-400">
            Chỉ tập trung vào thống kê phương tiện
          </p>
          {stats?.timestemp && (
            <p className="mt-1 text-xs text-slate-500">
              Cập nhật lúc:{" "}
              {new Date(stats.timestemp).toLocaleTimeString("vi-VN")}
            </p>
          )}
          {error && (
            <p className="mt-1 text-xs text-red-400">
              {error}
            </p>
          )}
        </div>
        <span className="text-xs text-emerald-400">
          {stats ? "Live" : "Đang kết nối..."}
        </span>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {summaryCards.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {breakdownCards.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>
    </Card>
  );
}
