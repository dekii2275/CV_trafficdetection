"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import StatCard from "./StatCard";
import { formatCompactNumber, formatNumber } from "../../lib/utils";

type DashboardCurrentStats = {
  car: number;
  motor: number;
  bus: number;
  truck: number;
  total_vehicles: number;
  timestamp?: string;
};

type DashboardResponse = {
  camera_id: number;
  date: string;
  current_hour: number;
  current_stats: DashboardCurrentStats;
  daily_total: number;
};

type RealtimeStatsProps = {
  cameraId: number;
  cameraLabel?: string;
};

export default function RealtimeStats({
  cameraId,
  cameraLabel,
}: RealtimeStatsProps) {
  const [stats, setStats] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const API_BASE =
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

    async function fetchStats() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/dashboard/${cameraId}`, {
          cache: "no-store",
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = (await res.json()) as DashboardResponse;
        if (!cancelled) {
          setStats(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Fetch dashboard error:", err);
          setError("Không lấy được dữ liệu thống kê");
        }
      }
    }

    fetchStats();
    const interval = setInterval(fetchStats, 5000); // 5s

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [cameraId]);

  const total = stats?.daily_total ?? 0;

  const car = stats?.current_stats?.car ?? 0;
  const truck = stats?.current_stats?.truck ?? 0;
  const bike = stats?.current_stats?.motor ?? 0;
  const bus = stats?.current_stats?.bus ?? 0;

  const lastUpdated = stats?.current_stats?.timestamp;

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
      label: "CAR (giờ hiện tại)",
      value: formatCompactNumber(car),
      helperText: "Trong khung giờ hiện tại",
    },
    {
      label: "TRUCK (giờ hiện tại)",
      value: formatCompactNumber(truck),
      helperText: "Trong khung giờ hiện tại",
    },
    {
      label: "BIKE (giờ hiện tại)",
      value: formatCompactNumber(bike),
      helperText: "Trong khung giờ hiện tại",
    },
    {
      label: "BUS (giờ hiện tại)",
      value: formatCompactNumber(bus),
      helperText: "Trong khung giờ hiện tại",
    },
  ];

  return (
    <Card>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">
            Realtime Vehicle Count • {cameraLabel ?? `Camera ${cameraId}`}
          </h2>
          <p className="text-sm text-slate-400">
            Chỉ tập trung vào thống kê phương tiện
          </p>
          {lastUpdated && (
            <p className="mt-1 text-xs text-slate-500">
              Cập nhật lúc:{" "}
              {new Date(lastUpdated).toLocaleTimeString("vi-VN")}
            </p>
          )}
          {error && (
            <p className="mt-1 text-xs text-red-400">
              {error}
            </p>
          )}
        </div>
        <span className="text-xs text-emerald-400">
          {stats ? "Đang kết nối..." : "Đang khởi tạo..."}
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
