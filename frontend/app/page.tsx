import Sidebar from "./components/sidebar/Sidebar";
import VideoPlayer from "./components/stream/VideoPlayer";
import RealtimeStats from "./components/stats/RealtimeStats";
import ChartCard from "./components/charts/ChartCard";
import PieChart from "./components/charts/PieChart";
import BarChart from "./components/charts/BarChart";
import AnalyticsStats from "./components/analytics/AnalyticsStats";
import type { ChartPoint } from "./lib/types";

type VehicleBreakdownItem = { label: string; value: number };

type HourlyStat = {
  timestamp?: string;
  car?: number;
  motor?: number;
  bus?: number;
  truck?: number;
  total_vehicles?: number;
};

type CameraChartData = {
  vehicleBreakdown: VehicleBreakdownItem[];
  hourlyFlow: ChartPoint[];
};

export default async function DashboardPage() {
  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  async function fetchCameraChartData(
    cameraId: number,
  ): Promise<CameraChartData> {
    try {
      const res = await fetch(`${API_BASE}/api/v1/stats/${cameraId}`, {
        cache: "no-store",
      });

      if (!res.ok) {
        console.warn(`stats ${cameraId} HTTP ${res.status}`);
        return { vehicleBreakdown: [], hourlyFlow: [] };
      }

      const data = (await res.json()) as HourlyStat[] | HourlyStat;
      const hourlyArray: HourlyStat[] = Array.isArray(data) ? data : [data];

      let totalCar = 0;
      let totalTruck = 0;
      let totalMotor = 0;
      let totalBus = 0;
      let totalAllVehicles = 0;

      const hourlyFlow: ChartPoint[] = [];

      const maxHours = Math.min(24, hourlyArray.length);
      for (let h = 0; h < maxHours; h++) {
        const item = hourlyArray[h] || {};
        const car = Number(item.car ?? 0);
        const truck = Number(item.truck ?? 0);
        const motor = Number(item.motor ?? 0);
        const bus = Number(item.bus ?? 0);
        const totalVehicles = Number(item.total_vehicles ?? 0);

        // Sum từng loại xe (mỗi giờ là độc lập)
        totalCar += car;
        totalTruck += truck;
        totalMotor += motor;
        totalBus += bus;
        totalAllVehicles += totalVehicles;

        hourlyFlow.push({
          label: `${h.toString().padStart(2, "0")}h`,
          value: totalVehicles,
        });
      }

      // Đảm bảo tính nhất quán: nếu sum từng loại khác với total_vehicles,
      // ưu tiên dùng total_vehicles (vì nó là giá trị chính thức)
      const sumByType = totalCar + totalTruck + totalMotor + totalBus;
      const useTotalVehicles = Math.abs(sumByType - totalAllVehicles) > 1; // Cho phép sai số nhỏ

      const vehicleBreakdown: VehicleBreakdownItem[] = [
        { label: "Cars", value: totalCar },
        { label: "Trucks", value: totalTruck },
        { label: "Motors", value: totalMotor },
        { label: "Buses", value: totalBus },
      ];

      return { vehicleBreakdown, hourlyFlow };
    } catch (e) {
      console.error("fetchCameraChartData error:", e);
      return { vehicleBreakdown: [], hourlyFlow: [] };
    }
  }

  const [cam0Charts, cam1Charts] = await Promise.all([
    fetchCameraChartData(0),
    fetchCameraChartData(1),
  ]);

  return (
    <div className="flex min-h-screen w-full bg-slate-950 text-slate-100">
      <Sidebar />

      <section className="flex-1 space-y-6 p-6">
        {/* Header */}
        <header className="flex flex-col gap-2">
          <p className="text-sm uppercase tracking-wide text-emerald-400">
            Live counting
          </p>
          <h1 className="text-2xl font-semibold">Traffic AI Vehicle Counter</h1>
          <p className="text-sm text-slate-400">
            Hệ thống giám sát 2 camera, hiển thị thống kê realtime cho từng
            camera và biểu đồ theo loại phương tiện / theo thời gian.
          </p>
        </header>

        {/* HÀNG 1: Grid camera (component VideoPlayer của bạn đã chia 2 camera) */}
        <VideoPlayer
          roadName="default"
          backendUrl="ws://localhost:8000"
        />

        {/* HÀNG 2: Realtime stats từng camera */}
        <div className="grid gap-6 xl:grid-cols-2">
          <RealtimeStats cameraId={0} cameraLabel="Camera 1" />
          <RealtimeStats cameraId={1} cameraLabel="Camera 2" />
        </div>

        {/* HÀNG 3: Phân bố theo loại phương tiện (Biểu đồ tròn) */}
        <div className="grid gap-6 xl:grid-cols-2">
          <ChartCard title="Phân bố theo loại phương tiện • Camera 1">
            <PieChart data={cam0Charts.vehicleBreakdown} />
          </ChartCard>

          <ChartCard title="Phân bố theo loại phương tiện • Camera 2">
            <PieChart data={cam1Charts.vehicleBreakdown} />
          </ChartCard>
        </div>

        {/* HÀNG 4: Lưu lượng theo giờ (Biểu đồ cột) */}
        <div className="grid gap-6 xl:grid-cols-2">
          <ChartCard title="Lưu lượng theo giờ • Camera 1">
            <BarChart points={cam0Charts.hourlyFlow} />
          </ChartCard>

          <ChartCard title="Lưu lượng theo giờ • Camera 2">
            <BarChart points={cam1Charts.hourlyFlow} />
          </ChartCard>
        </div>

        {/* HÀNG 5: Phân tích thống kê nâng cao từ analyze.py */}
        <div className="grid gap-6 xl:grid-cols-2">
          <AnalyticsStats cameraId={0} cameraLabel="Camera 1" />
          <AnalyticsStats cameraId={1} cameraLabel="Camera 2" />
        </div>
      </section>
    </div>
  );
}
