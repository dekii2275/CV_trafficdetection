'use client';

import { useEffect, useState, useRef } from 'react';
import Card from '../ui/Card';

interface VehicleStats {
  total_today: number;
  current_speed: number;
  total_change_percent: number;
  speed_change_percent: number;
  car_count: number;
  truck_count: number;
  motor_count: number;
  bus_count: number;
  timestamp?: string;
}

export default function RealtimeDashboard() {
  const [stats, setStats] = useState<VehicleStats>({
    total_today: 0,
    current_speed: 0,
    total_change_percent: 0,
    speed_change_percent: 0,
    car_count: 0,
    truck_count: 0,
    motor_count: 0,
    bus_count: 0,
  });

  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connectWebSocket = () => {
      // ✅ KẾT NỐI TỚI ENDPOINT MỚI
      const ws = new WebSocket('ws://localhost:8000/api/v1/ws/stats');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Dashboard WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data: VehicleStats = JSON.parse(event.data);
          setStats(data);
        } catch (err) {
          console.error('Failed to parse stats:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };

      ws.onclose = (event) => {
        console.log('🔌 WebSocket disconnected');
        setIsConnected(false);
        
        // Auto reconnect
        if (event.code !== 1000) {
          setTimeout(connectWebSocket, 3000);
        }
      };
    };

    connectWebSocket();

    return () => {
      wsRef.current?.close(1000);
    };
  }, []);

  const formatNumber = (num: number) => num.toLocaleString('vi-VN');
  const formatCompact = (num: number) => num >= 1000 ? `${(num / 1000).toFixed(1)}K` : num.toString();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Realtime Vehicle Count</h2>
          <p className="text-sm text-slate-400">Chi tập trung vào thống kê phương tiện</p>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
          isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>
          <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
          {isConnected ? 'LIVE' : 'RECONNECTING...'}
        </div>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">TỔNG LƯỢT HÔM NAY</p>
          <div className="flex items-baseline gap-3">
            <h2 className="text-5xl font-bold text-white">{formatNumber(stats.total_today)}</h2>
            <span className={`text-lg font-semibold ${
              stats.total_change_percent >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {stats.total_change_percent >= 0 ? '+' : ''}{stats.total_change_percent.toFixed(1)}%
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-2">Tính từ 00:00</p>
        </Card>

        <Card>
          <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">TỐC ĐỘ ĐẾM HIỆN TẠI</p>
          <div className="flex items-baseline gap-2">
            <h2 className="text-5xl font-bold text-white">{stats.current_speed}</h2>
            <span className="text-2xl text-slate-400">/min</span>
            <span className={`text-lg font-semibold ml-2 ${
              stats.speed_change_percent >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {stats.speed_change_percent >= 0 ? '+' : ''}{stats.speed_change_percent.toFixed(1)}%
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-2">Trung bình 5 phút</p>
        </Card>
      </div>

      {/* Vehicle Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'CAR', value: stats.car_count },
          { label: 'TRUCK', value: stats.truck_count },
          { label: 'MOTOR', value: stats.motor_count },
          { label: 'BUS', value: stats.bus_count },
        ].map((item) => (
          <Card key={item.label}>
            <p className="text-xs uppercase tracking-wider text-slate-400 mb-1">LƯỢT {item.label}</p>
            <h3 className="text-4xl font-bold text-white">{formatCompact(item.value)}</h3>
            <p className="text-xs text-slate-500 mt-1">Trong 1 giờ</p>
          </Card>
        ))}
      </div>
    </div>
  );
}