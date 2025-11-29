"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import StatCard from "../stats/StatCard";
import { formatNumber, formatCompactNumber } from "../../lib/utils";

type VehicleTotals = {
  car: number;
  motor: number;
  bus: number;
  truck: number;
};

type VehiclePercentages = {
  car: number;
  motor: number;
  bus: number;
  truck: number;
};

type StatsSummary = {
  mean: number;
  min: number;
  max: number;
  std: number;
};

type AnalyzeResponse = {
  camera_id: number;
  summary: {
    total_records: number;
    total_vehicles: number;
    vehicle_totals: VehicleTotals;
    vehicle_percentages: VehiclePercentages;
    peak_detections: number;
    stats: StatsSummary;
  };
  time_series: any[];
  rolling_mean: number[] | null;
};

type AnalyticsStatsProps = {
  cameraId: number;
  cameraLabel?: string;
};

export default function AnalyticsStats({
  cameraId,
  cameraLabel,
}: AnalyticsStatsProps) {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const API_BASE =
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

    async function fetchAnalytics() {
      try {
        setLoading(true);
        const res = await fetch(
          `${API_BASE}/api/v1/analyze/${cameraId}`,
          {
            cache: "no-store",
          }
        );

        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("Không có dữ liệu để phân tích");
          }
          throw new Error(`HTTP ${res.status}`);
        }

        const responseData = (await res.json()) as AnalyzeResponse;
        if (!cancelled) {
          setData(responseData);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Fetch analytics error:", err);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được dữ liệu phân tích"
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000); // 30s

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [cameraId]);

  if (loading && !data) {
    return (
      <Card>
        <div className="p-6 text-center text-slate-400">
          Đang tải dữ liệu phân tích...
        </div>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card>
        <div className="p-6">
          <h3 className="mb-2 text-lg font-semibold">
            Phân tích thống kê • {cameraLabel ?? `Camera ${cameraId}`}
          </h3>
          <p className="text-sm text-red-400">{error}</p>
        </div>
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  const { summary } = data;
  const { vehicle_totals, vehicle_percentages, stats, peak_detections } =
    summary;

  return (
    <Card>
      <div className="mb-6">
        <h3 className="text-lg font-semibold">
          Phân tích thống kê nâng cao • {cameraLabel ?? `Camera ${cameraId}`}
        </h3>
        <p className="mt-1 text-sm text-slate-400">
          Thống kê chi tiết từ dữ liệu gần đây (60 phút)
        </p>
      </div>

      {/* Tổng quan */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Tổng phương tiện"
          value={formatNumber(summary.total_vehicles)}
          helperText={`${summary.total_records} bản ghi`}
        />
        <StatCard
          label="Phát hiện đỉnh"
          value={formatNumber(peak_detections)}
          helperText="Lưu lượng cao bất thường"
        />
        <StatCard
          label="Trung bình/phút"
          value={formatCompactNumber(stats.mean)}
          helperText={`Min: ${stats.min} | Max: ${stats.max}`}
        />
        <StatCard
          label="Độ lệch chuẩn"
          value={formatCompactNumber(stats.std)}
          helperText="Biến động dữ liệu"
        />
      </div>

      {/* Phân bố theo loại xe với phần trăm */}
      <div className="mb-6">
        <h4 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Phân bố theo loại phương tiện
        </h4>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <div className="mb-1 text-xs text-slate-400">CAR</div>
            <div className="mb-1 text-2xl font-bold text-white">
              {formatNumber(vehicle_totals.car)}
            </div>
            <div className="text-sm text-emerald-400">
              {vehicle_percentages.car.toFixed(1)}%
            </div>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <div className="mb-1 text-xs text-slate-400">MOTOR</div>
            <div className="mb-1 text-2xl font-bold text-white">
              {formatNumber(vehicle_totals.motor)}
            </div>
            <div className="text-sm text-emerald-400">
              {vehicle_percentages.motor.toFixed(1)}%
            </div>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <div className="mb-1 text-xs text-slate-400">BUS</div>
            <div className="mb-1 text-2xl font-bold text-white">
              {formatNumber(vehicle_totals.bus)}
            </div>
            <div className="text-sm text-emerald-400">
              {vehicle_percentages.bus.toFixed(1)}%
            </div>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <div className="mb-1 text-xs text-slate-400">TRUCK</div>
            <div className="mb-1 text-2xl font-bold text-white">
              {formatNumber(vehicle_totals.truck)}
            </div>
            <div className="text-sm text-emerald-400">
              {vehicle_percentages.truck.toFixed(1)}%
            </div>
          </div>
        </div>
      </div>

      {/* Thống kê chi tiết */}
      <div>
        <h4 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Thống kê chi tiết
        </h4>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <div className="mb-1 text-xs text-slate-400">Giá trị nhỏ nhất</div>
            <div className="text-xl font-semibold text-white">
              {formatNumber(stats.min)}
            </div>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <div className="mb-1 text-xs text-slate-400">Giá trị lớn nhất</div>
            <div className="text-xl font-semibold text-white">
              {formatNumber(stats.max)}
            </div>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <div className="mb-1 text-xs text-slate-400">Trung bình</div>
            <div className="text-xl font-semibold text-white">
              {formatCompactNumber(stats.mean)}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

