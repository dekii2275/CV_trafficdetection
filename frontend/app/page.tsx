import Sidebar from "./components/sidebar/Sidebar";
import VideoPlayer from "./components/stream/VideoPlayer";
import RealtimeStats from "./components/stats/RealtimeStats";
import ChartCard from "./components/charts/ChartCard";
import RealtimeCounterChart from "./components/charts/RealtimeCounterChart";
import VehicleLineChart from "./components/charts/VehicleLineChart";
import SummaryTable from "./components/table/SummaryTable";
import TableRow from "./components/table/TableRow";
import Card from "./components/ui/Card";
import { formatNumber } from "./lib/utils";
import type { CameraSummary, ChartPoint } from "./lib/types";

const vehicleBreakdown = [
  { label: "Cars", value: 12140 },
  { label: "Trucks", value: 3820 },
  { label: "Bikes", value: 1840 },
  { label: "Buses", value: 620 },
];

const hourlyFlow: ChartPoint[] = [
  { label: "08h", value: 260 },
  { label: "09h", value: 320 },
  { label: "10h", value: 340 },
  { label: "11h", value: 300 },
  { label: "12h", value: 280 },
  { label: "13h", value: 290 },
];

const cameraSummaries: CameraSummary[] = [
  { camera: "Cam 01 · Xa Lộ", vehicles: 482, dominantType: "car" },
  { camera: "Cam 02 · Trung Tâm", vehicles: 356, dominantType: "bike" },
  { camera: "Cam 03 · Cảng", vehicles: 298, dominantType: "truck" },
  { camera: "Cam 04 · BRT", vehicles: 214, dominantType: "bus" },
];

const totalToday = vehicleBreakdown.reduce((sum, item) => sum + item.value, 0);

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen w-full bg-slate-950 text-slate-100">
      <Sidebar />
      <section className="flex-1 space-y-6 p-6">
        <header className="flex flex-col gap-2">
          <p className="text-sm uppercase tracking-wide text-emerald-400">Live counting</p>
          <h1 className="text-2xl font-semibold">Traffic AI Vehicle Counter</h1>
          <p className="text-sm text-slate-400">
            Dashboard này chỉ tập trung vào thống kê số lượng phương tiện được hệ thống đếm theo thời gian thực.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <VideoPlayer 
            roadName="default"
            backendUrl="ws://localhost:8000" />
          <Card>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Tổng lượt ghi nhận hôm nay</h3>
            <p className="my-4 text-3xl font-bold text-white">{formatNumber(totalToday)}</p>
            <p className="text-sm text-slate-400">
              Con số này chỉ bao gồm lượng phương tiện đi ngang vùng đếm, không bao gồm thông tin tai nạn hay kẹt xe.
            </p>
          </Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <RealtimeStats cameraId={0} cameraLabel="Camera 1" />
          <RealtimeStats cameraId={1} cameraLabel="Camera 2" />
        </div>


        <div className="grid gap-6 xl:grid-cols-3">
          <ChartCard title="Phân bổ theo loại phương tiện">
            <RealtimeCounterChart data={vehicleBreakdown} />
          </ChartCard>
          <ChartCard title="Lưu lượng theo giờ">
            <VehicleLineChart points={hourlyFlow} />
          </ChartCard>
          <Card>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Ghi chú</h3>
            <p className="mt-2 text-sm text-slate-300">
              Mỗi camera chỉ gửi về số lượng phương tiện theo từng khung hình. Các tín hiệu về tai nạn hoặc sự cố đã được
              loại bỏ để đảm bảo dashboard chỉ phục vụ nhu cầu đếm xe.
            </p>
          </Card>
        </div>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Camera theo phút</h2>
              <p className="text-sm text-slate-400">Top camera với số lượt đếm cao nhất</p>
            </div>
            <span className="text-xs text-slate-500">Số liệu được làm mới liên tục</span>
          </div>
          <SummaryTable>
            {cameraSummaries.map((summary) => (
              <TableRow key={summary.camera} {...summary} />
            ))}
          </SummaryTable>
        </Card>
      </section>
    </div>
  );
}
