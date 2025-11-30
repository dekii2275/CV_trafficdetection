"use client";

import VideoPlayer from "../stream/VideoPlayer";
import RealtimeStats from "../stats/RealtimeStats";
import VehicleDistributionChart from "../charts/VehicleDistributionChart"; // Biểu đồ tròn
import VehicleLineChart from "../charts/VehicleLineChart"; // Biểu đồ đường
import AnalyticsStats from "../analytics/AnalyticsStats"; // Phân tích nâng cao

interface RealtimeDashboardProps {
  cameraId?: number;
}

export default function RealtimeDashboard({ cameraId = 0 }: RealtimeDashboardProps) {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Cột trái (Lớn): Hiển thị Video Stream */}
        <div className="xl:col-span-2 h-full min-h-[400px]">
           {/* Component này hiển thị hình ảnh từ WebSocket /ws/frames */}
           <VideoPlayer 
             roadName={cameraId.toString()} 
             label={`Camera ${cameraId} - Live Feed`} 
           />
        </div>

        {/* Cột phải (Nhỏ): Hiển thị số liệu nhảy múa (RealtimeStats) */}
        <div className="xl:col-span-1 h-full">
          <RealtimeStats 
            cameraId={cameraId} 
            cameraLabel={`Khu vực Cam ${cameraId}`} 
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Biểu đồ phân bố loại xe (Pie Chart) - Dữ liệu tổng hợp */}
        <VehicleDistributionChart />
        
        {/* Biểu đồ xu hướng theo giờ (Line Chart) - Dữ liệu lịch sử */}
        <VehicleLineChart cameraId={cameraId} />
      </div>

      <div>
        {/* Các chỉ số như: Đỉnh lưu lượng, độ lệch chuẩn, xu hướng tăng/giảm */}
        <AnalyticsStats cameraId={cameraId} />
      </div>

    </div>
  );
}