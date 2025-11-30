"use client";

import { useEffect, useState } from "react";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from "recharts";
import Card from "../ui/Card";

interface VehicleLineChartProps {
  cameraId: number;
}

export default function VehicleLineChart({ cameraId }: VehicleLineChartProps) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        
        // ✅ SỬA: Đảm bảo parameter đúng
        const res = await fetch(`${API_BASE}/api/v1/charts/time-series/${cameraId}?minutes=60`, {
          cache: "no-store",
        });
        
        if (res.ok) {
          const json = await res.json();
          
          // ✅ SỬA: Debug log để kiểm tra
          console.log(`[VehicleLineChart Cam ${cameraId}] API Response:`, json);
          
          // ✅ SỬA: Kiểm tra kỹ hơn
          if (json.points && Array.isArray(json.points) && json.points.length > 0) {
            const chartData = json.points.map((p: any) => ({
              time: p.label || "00:00",
              count: Number(p.value) || 0
            }));
            console.log(`[VehicleLineChart Cam ${cameraId}] Chart data:`, chartData);
            setData(chartData);
            setError(null);
          } else if (json.message) {
            // API trả về message (chưa có dữ liệu)
            console.log(`[VehicleLineChart Cam ${cameraId}] Message:`, json.message);
            setData([]);
            setError(json.message);
          } else {
            // Không có points hoặc points rỗng
            console.warn(`[VehicleLineChart Cam ${cameraId}] No points in response`);
            setData([]);
            setError("Không có dữ liệu");
          }
        } else {
          // ✅ SỬA: Xử lý lỗi HTTP
          try {
            const errorData = await res.json();
            console.error(`[VehicleLineChart Cam ${cameraId}] HTTP ${res.status}:`, errorData);
            setError(errorData.message || errorData.error || `HTTP ${res.status}`);
          } catch {
            setError(`HTTP ${res.status}: Không lấy được dữ liệu`);
          }
          setData([]);
        }
      } catch (e) {
        console.error(`[VehicleLineChart Cam ${cameraId}] Fetch error:`, e);
        setError("Lỗi kết nối");
        setData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // 60s refresh
    return () => clearInterval(interval);
  }, [cameraId]);

  // --- RENDERING ---

  // 1. Chưa mount (Server Side)
  if (!isMounted) {
    return (
      <Card>
        <div className="h-[200px]" />
      </Card>
    );
  }

  // 2. Đang tải lần đầu
  if (loading && data.length === 0) {
    return (
      <Card>
        <div className="h-[200px] flex items-center justify-center text-slate-500 animate-pulse">
          Đang tải lịch sử...
        </div>
      </Card>
    );
  }

  // 3. Có lỗi
  if (error) {
    return (
      <Card>
        <div className="h-[200px] flex flex-col items-center justify-center text-slate-500 gap-2">
          <span className="text-2xl">⚠️</span>
          <p className="text-sm text-yellow-400">{error}</p>
          <p className="text-xs text-slate-600">Camera {cameraId}</p>
        </div>
      </Card>
    );
  }

  // 4. Không có dữ liệu
  if (data.length === 0) {
    return (
      <Card>
        <div className="h-[200px] flex flex-col items-center justify-center text-slate-500 gap-2">
          <span className="text-2xl">📉</span>
          <p>Chưa có dữ liệu lịch sử</p>
          <p className="text-xs text-slate-600">Camera {cameraId}</p>
        </div>
      </Card>
    );
  }

  // 5. Có dữ liệu -> Vẽ biểu đồ
  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-400 uppercase">
          Lưu lượng theo phút • Cam {cameraId}
        </h3>
        <span className="text-[10px] bg-slate-800 px-2 py-1 rounded text-slate-500">
          60 phút qua
        </span>
      </div>

      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id={`colorCount${cameraId}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
            
            <XAxis 
              dataKey="time" 
              tick={{fontSize: 10, fill: '#9ca3af'}} 
              axisLine={false} 
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={20}
            />
            
            <YAxis 
              tick={{fontSize: 10, fill: '#9ca3af'}} 
              axisLine={false} 
              tickLine={false} 
              width={40}
            />
            
            <Tooltip 
              contentStyle={{
                backgroundColor: '#1f2937', 
                borderColor: '#374151', 
                color: '#fff', 
                fontSize: '12px',
                borderRadius: '8px'
              }}
              labelStyle={{color: '#9ca3af', marginBottom: '4px'}}
              formatter={(value: number) => [`${value} xe`, 'Lưu lượng']}
            />
            
            <Area 
              type="monotone"
              dataKey="count" 
              stroke="#3b82f6" 
              strokeWidth={2}
              fillOpacity={1} 
              fill={`url(#colorCount${cameraId})`} 
              animationDuration={1000}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}