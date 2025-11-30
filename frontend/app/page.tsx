// frontend/app/page.tsx
import Sidebar from "./components/sidebar/Sidebar";
import VideoPlayer from "./components/stream/VideoPlayer";
import RealtimeStats from "./components/stats/RealtimeStats";
import VehicleDistributionChart from "./components/charts/VehicleDistributionChart";
import VehicleLineChart from "./components/charts/VehicleLineChart";
import AnalyticsStats from "./components/analytics/AnalyticsStats";

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen w-full bg-[#0f172a] text-slate-100">
      {/* 1. Sidebar bên trái */}
      <Sidebar />

      {/* 2. Nội dung chính */}
      <section className="flex-1 space-y-6 p-6 overflow-y-auto h-screen">
        
        {/* Header */}
        <header className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <p className="text-sm uppercase tracking-wide text-emerald-400 font-bold">
              System Online
            </p>
          </div>
          <h1 className="text-3xl font-bold text-white">Traffic AI Command Center</h1>
          <p className="text-slate-400">
            Hệ thống giám sát giao thông thông minh & Phân tích dữ liệu thời gian thực
          </p>
        </header>

        {/* --- KHỐI 1: VIDEO STREAM (2 CAMERA RIÊNG BIỆT - KÍCH THƯỚC LỚN) --- */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* Camera 0 - Khung lớn */}
          <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-black h-[70vh] min-h-[500px]">
            <VideoPlayer 
              roadName="0"
              backendUrl="ws://localhost:8000"
              label="Camera 0 - Cổng Chính"
            />
          </div>
          
          {/* Camera 1 - Khung lớn */}
          <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-black h-[70vh] min-h-[500px]">
            <VideoPlayer 
              roadName="1"
              backendUrl="ws://localhost:8000"
              label="Camera 1 - Ngã Tư A"
            />
          </div>
        </div>

        {/* --- KHỐI 2: REALTIME COUNTER (Số nhảy múa) --- */}
        <div className="grid gap-6 xl:grid-cols-2">
          <RealtimeStats cameraId={0} cameraLabel="Camera 01: Cổng Chính" />
          <RealtimeStats cameraId={1} cameraLabel="Camera 02: Ngã Tư A" />
        </div>

        {/* --- KHỐI 3: BIỂU ĐỒ PHÂN TÍCH (Database History) --- */}
        <div className="grid gap-6 xl:grid-cols-3">
          {/* Cột 1: Biểu đồ đường - Cam 01 */}
          <div className="xl:col-span-1">
            <VehicleLineChart cameraId={0} />
          </div>

          {/* Cột 2: Biểu đồ đường - Cam 02 */}
          <div className="xl:col-span-1">
            <VehicleLineChart cameraId={1} />
          </div>

          {/* Cột 3: Phân bố phương tiện (Toàn hệ thống) */}
          <div className="xl:col-span-1">
            <VehicleDistributionChart />
          </div>
        </div>

        {/* --- KHỐI 4: PHÂN TÍCH CHUYÊN SÂU (AI Analytics) --- */}
        <h2 className="text-xl font-bold text-white pt-4 border-t border-slate-800">
          Phân tích chuyên sâu (Advanced Analytics)
        </h2>
        <div className="grid gap-6 xl:grid-cols-1">
          <AnalyticsStats cameraId={0} cameraLabel="Camera 01" />
          <AnalyticsStats cameraId={1} cameraLabel="Camera 02" />
        </div>

      </section>
    </div>
  );
}