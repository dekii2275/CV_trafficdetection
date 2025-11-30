// trang dashboard chính, gom toàn bộ layout + biểu đồ + video

import Sidebar from "./components/sidebar/Sidebar";
import VideoPlayer from "./components/stream/VideoPlayer";
import RealtimeStats from "./components/stats/RealtimeStats";
import VehicleDistributionChart from "./components/charts/VehicleDistributionChart";
import VehicleLineChart from "./components/charts/VehicleLineChart";
import GroupedBarChart from "./components/charts/GroupedBarChart";
import AreaChart from "./components/charts/AreaChart";
import HistTotalChart from "./components/charts/HistTotalChart";
import BoxplotChart from "./components/charts/BoxplotChart";
import RollingAvgChart from "./components/charts/RollingAvgChart";
import PeaksChart from "./components/charts/PeaksChart";

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen w-full bg-[#0f172a] text-slate-100">

      {/* sidebar cố định bên trái */}
      <Sidebar />

      {/* khu vực nội dung dashboard */}
      <section className="flex-1 space-y-6 p-6 overflow-y-auto h-screen">

        {/* header trạng thái hệ thống */}
        <header className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            {/* icon chấm xanh nhấp nháy */}
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <p className="text-sm uppercase tracking-wide text-emerald-400 font-bold">
              System Online
            </p>
          </div>

          <h1 className="text-3xl font-bold text-white">
            Traffic AI Command Center
          </h1>

          <p className="text-slate-400">
            Hệ thống giám sát giao thông & phân tích theo thời gian thực
          </p>
        </header>

        {/* khối 1: 2 video stream từ 2 camera */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-black h-[70vh] min-h-[500px]">
            <VideoPlayer 
              roadName="0"
              backendUrl="ws://localhost:8000"
              label="Camera 0 - Cổng Chính"
            />
          </div>

          <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-black h-[70vh] min-h-[500px]">
            <VideoPlayer 
              roadName="1"
              backendUrl="ws://localhost:8000"
              label="Camera 1 - Ngã Tư A"
            />
          </div>
        </div>

        {/* khối 2: realtime counter từ WebSocket */}
        <div className="grid gap-6 xl:grid-cols-2">
          <RealtimeStats cameraId={0} cameraLabel="Camera 01: Cổng Chính" />
          <RealtimeStats cameraId={1} cameraLabel="Camera 02: Ngã Tư A" />
        </div>

        {/* khối 3: biểu đồ phân tích cơ bản */}
        <div className="grid gap-6 xl:grid-cols-3">
          <div><VehicleLineChart cameraId={0} /></div>
          <div><VehicleLineChart cameraId={1} /></div>
          <div><VehicleDistributionChart /></div>
        </div>

        {/* tiêu đề cho nhóm biểu đồ từ database */}
        <h2 className="text-xl font-bold text-white pt-6 border-t border-slate-800">
          Biểu đồ chuyên sâu từ lịch sử (Database Charts)
        </h2>

        {/* grouped bar */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-200">Grouped Bar</h3>
          <div className="grid gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 01</p>
              <GroupedBarChart cameraId={0} />
            </div>
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 02</p>
              <GroupedBarChart cameraId={1} />
            </div>
          </div>
        </div>

        {/* stacked area */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-200">Stacked Area</h3>
          <div className="grid gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 01</p>
              <AreaChart cameraId={0} />
            </div>
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 02</p>
              <AreaChart cameraId={1} />
            </div>
          </div>
        </div>

        {/* rolling average */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-200">Rolling Average</h3>
          <div className="grid gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 01</p>
              <RollingAvgChart cameraId={0} />
            </div>
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 02</p>
              <RollingAvgChart cameraId={1} />
            </div>
          </div>
        </div>

        {/* histogram */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-200">Histogram</h3>
          <div className="grid gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 01</p>
              <HistTotalChart cameraId={0} />
            </div>
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 02</p>
              <HistTotalChart cameraId={1} />
            </div>
          </div>
        </div>

        {/* boxplot */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-200">Boxplot</h3>
          <div className="grid gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 01</p>
              <BoxplotChart cameraId={0} />
            </div>
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 02</p>
              <BoxplotChart cameraId={1} />
            </div>
          </div>
        </div>

        {/* peaks */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-200">Peaks</h3>
          <div className="grid gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 01</p>
              <PeaksChart cameraId={0} />
            </div>
            <div>
              <p className="mb-2 text-xs text-slate-400">Camera 02</p>
              <PeaksChart cameraId={1} />
            </div>
          </div>
        </div>

      </section>
    </div>
  );
}
