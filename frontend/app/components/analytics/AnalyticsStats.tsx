"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import StatCard from "../stats/StatCard";
import { formatNumber, formatCompactNumber } from "../../lib/utils";

// --- Types ---
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

// Kiểu dữ liệu từ Backend API
type BackendResponse = {
  current_flow?: number;
  average_flow?: number;
  peak_flow?: number;
  volatility?: string;
  status?: string;
  trend_percent?: number;
  composition?: {
    car: number;
    motor: number;
    truck: number;
    bus: number;
  };
  message?: string;
  error?: string;
};

// Kiểu dữ liệu chuẩn cho Frontend
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
  message?: string;
  error?: string;
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

        const responseData: BackendResponse = await res.json();

        if (!res.ok) {
          // Xử lý lỗi 404 hoặc 500 từ server
          if (responseData.message) throw new Error(responseData.message);
          if (responseData.error) throw new Error(responseData.error);
          throw new Error(`HTTP ${res.status}`);
        }

        if (!cancelled) {
          // Xử lý trường hợp API trả về message (chưa có dữ liệu)
          if (responseData.message) {
            setData({
              camera_id: cameraId,
              summary: {
                total_records: 0,
                total_vehicles: 0,
                vehicle_totals: { car: 0, motor: 0, bus: 0, truck: 0 },
                vehicle_percentages: { car: 0, motor: 0, bus: 0, truck: 0 },
                peak_detections: 0,
                stats: { mean: 0, min: 0, max: 0, std: 0 },
              },
              time_series: [],
              rolling_mean: null,
              message: responseData.message,
            });
            setError(null);
            return;
          }

          // Map dữ liệu từ backend format sang frontend format
          const composition = responseData.composition || { 
            car: 0, 
            motor: 0, 
            bus: 0, 
            truck: 0 
          };

          // Tính tổng vehicles một cách an toàn
          const compositionValues = Object.values(composition);
          const totalVehicles = compositionValues.reduce(
            (sum: number, val: number) => {
              const numVal = typeof val === 'number' ? val : 0;
              return sum + (isNaN(numVal) ? 0 : numVal);
            },
            0
          );

          // Parse volatility một cách an toàn
          const volatilityStr = responseData.volatility || "0";
          const volatilityNum = parseFloat(volatilityStr);
          const safeVolatility = isNaN(volatilityNum) ? 0 : volatilityNum;

          // Tạo mapped data
          const mappedData: AnalyzeResponse = {
            camera_id: cameraId,
            summary: {
              total_records: 0, // Backend không trả về
              total_vehicles: totalVehicles,
              vehicle_totals: {
                car: typeof composition.car === 'number' ? composition.car : 0,
                motor: typeof composition.motor === 'number' ? composition.motor : 0,
                bus: typeof composition.bus === 'number' ? composition.bus : 0,
                truck: typeof composition.truck === 'number' ? composition.truck : 0,
              },
              vehicle_percentages: {
                car: 0,
                motor: 0,
                bus: 0,
                truck: 0, // Sẽ tính sau
              },
              peak_detections: typeof responseData.peak_flow === 'number' 
                ? responseData.peak_flow 
                : 0,
              stats: {
                mean: typeof responseData.average_flow === 'number'
                  ? responseData.average_flow
                  : 0,
                min: 0, // Backend không trả về
                max: typeof responseData.peak_flow === 'number'
                  ? responseData.peak_flow
                  : 0,
                std: safeVolatility,
              },
            },
            time_series: [],
            rolling_mean: null,
          };

          // Tính phần trăm
          if (totalVehicles > 0) {
            mappedData.summary.vehicle_percentages = {
              car: (mappedData.summary.vehicle_totals.car / totalVehicles) * 100,
              motor: (mappedData.summary.vehicle_totals.motor / totalVehicles) * 100,
              bus: (mappedData.summary.vehicle_totals.bus / totalVehicles) * 100,
              truck: (mappedData.summary.vehicle_totals.truck / totalVehicles) * 100,
            };
          }

          setData(mappedData);
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

  // --- RENDERING ---

  if (loading && !data) {
    return (
      <Card>
        <div className="p-6 text-center text-slate-400 animate-pulse">
          Đang tải dữ liệu phân tích...
        </div>
      </Card>
    );
  }

  // Trường hợp có lỗi
  if (error) {
    return (
      <Card>
        <div className="p-6">
          <h3 className="mb-2 text-lg font-semibold">
            Phân tích thống kê • {cameraLabel ?? `Camera ${cameraId}`}
          </h3>
          <p className="text-sm text-yellow-400">⚠️ {error}</p>
        </div>
      </Card>
    );
  }

  // Trường hợp API trả về message (ví dụ: "Đang thu thập dữ liệu...") thay vì data
  if (data?.message) {
    return (
      <Card>
        <div className="p-6">
          <h3 className="mb-2 text-lg font-semibold">
            Phân tích thống kê • {cameraLabel ?? `Camera ${cameraId}`}
          </h3>
          <p className="text-sm text-blue-400">ℹ️ {data.message}</p>
        </div>
      </Card>
    );
  }

  // Kiểm tra kỹ trước khi render
  if (!data || !data.summary) {
    return (
      <Card>
        <div className="p-6 text-center text-slate-400">
          Không có dữ liệu để hiển thị
        </div>
      </Card>
    );
  }

  const { summary } = data;
  const { vehicle_totals, vehicle_percentages, stats, peak_detections } = summary;

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
          <VehicleBox 
            label="CAR" 
            count={vehicle_totals.car} 
            percent={vehicle_percentages.car} 
          />
          <VehicleBox 
            label="MOTOR" 
            count={vehicle_totals.motor} 
            percent={vehicle_percentages.motor} 
          />
          <VehicleBox 
            label="BUS" 
            count={vehicle_totals.bus} 
            percent={vehicle_percentages.bus} 
          />
          <VehicleBox 
            label="TRUCK" 
            count={vehicle_totals.truck} 
            percent={vehicle_percentages.truck} 
          />
        </div>
      </div>

      {/* Thống kê chi tiết */}
      <div>
        <h4 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Thống kê chi tiết
        </h4>
        <div className="grid gap-4 sm:grid-cols-3">
          <DetailBox label="Giá trị nhỏ nhất" value={formatNumber(stats.min)} />
          <DetailBox label="Giá trị lớn nhất" value={formatNumber(stats.max)} />
          <DetailBox label="Trung bình" value={formatCompactNumber(stats.mean)} />
        </div>
      </div>
    </Card>
  );
}

// --- Sub Components (Để code gọn hơn) ---

function VehicleBox({ 
  label, 
  count, 
  percent 
}: { 
  label: string; 
  count: number; 
  percent: number;
}) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <div className="mb-1 text-xs text-slate-400">{label}</div>
      <div className="mb-1 text-2xl font-bold text-white">{formatNumber(count)}</div>
      <div className="text-sm text-emerald-400">{percent.toFixed(1)}%</div>
    </div>
  );
}

function DetailBox({ 
  label, 
  value 
}: { 
  label: string; 
  value: string;
}) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <div className="mb-1 text-xs text-slate-400">{label}</div>
      <div className="text-xl font-semibold text-white">{value}</div>
    </div>
  );
}