"use client";

import { useEffect, useState, useRef } from "react";
import Card from "../ui/Card"; // Đảm bảo Card.tsx tồn tại ở ../ui/Card
import StatCard from "./StatCard"; // Import file vừa tạo ở trên
import { formatCompactNumber, formatNumber } from "../../lib/utils"; // Hàm format số

type RealtimeStatsProps = {
  cameraId: number;
  cameraLabel?: string;
};

// Kiểu dữ liệu nhận từ WebSocket Backend
type WebSocketMessage = {
  fps: number;
  total_entered: number;
  total_current: number;
  timestamp: number;
  details: {
    car?: { entered: number; current: number };
    motorcycle?: { entered: number; current: number };
    motorbike?: { entered: number; current: number };
    bus?: { entered: number; current: number };
    truck?: { entered: number; current: number };
  };
};

export default function RealtimeStats({
  cameraId,
  cameraLabel,
}: RealtimeStatsProps) {
  // State lưu trữ thống kê
  const [stats, setStats] = useState({
    car: 0,
    motor: 0,
    bus: 0,
    truck: 0,
    total: 0,
    fps: 0,
  });

  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // 1. Xác định URL WebSocket
    const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "localhost:8000";
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const cleanBase = API_BASE.replace("http://", "").replace("https://", "");
    const wsUrl = `${wsProtocol}//${cleanBase}/api/v1/ws/info/${cameraId}`;

    const connect = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log(`✅ Connected WS Info Cam ${cameraId}`);
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data: WebSocketMessage = JSON.parse(event.data);
            
            // Mapping dữ liệu từ Backend sang State Frontend
            const d = data.details || {};
            
            // Cộng dồn xe máy (motorcycle + motorbike)
            const bikeCount = 
              (d.motorcycle?.entered || 0) + 
              (d.motorbike?.entered || 0) + 
              (d.motor?.entered || 0);

            setStats({
              total: data.total_entered || 0,
              car: d.car?.entered || 0,
              motor: bikeCount,
              bus: d.bus?.entered || 0,
              truck: d.truck?.entered || 0,
              fps: data.fps || 0,
            });
          } catch (e) {
            console.error("Lỗi parse data:", e);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          // Tự động kết nối lại sau 3 giây nếu bị ngắt
          setTimeout(connect, 3000);
        };

        ws.onerror = (err) => {
          console.error("WS Error:", err);
          ws.close();
        };
      } catch (err) {
        console.error("Connection failed:", err);
      }
    };

    connect();

    // Cleanup khi component bị hủy
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [cameraId]);

  // Cấu hình hiển thị Cards
  const summaryCards = [
    {
      label: "Tổng lượt hôm nay",
      value: formatNumber(stats.total),
      helperText: isConnected ? `FPS: ${stats.fps.toFixed(1)}` : "Mất kết nối",
      trend: undefined,
    },
  ];

  const breakdownCards = [
    {
      label: "CAR",
      value: formatCompactNumber(stats.car),
      helperText: "Tổng lượt vào",
    },
    {
      label: "TRUCK",
      value: formatCompactNumber(stats.truck),
      helperText: "Tổng lượt vào",
    },
    {
      label: "BIKE",
      value: formatCompactNumber(stats.motor),
      helperText: "Tổng lượt vào",
    },
    {
      label: "BUS",
      value: formatCompactNumber(stats.bus),
      helperText: "Tổng lượt vào",
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
            Dữ liệu trực tiếp từ AI Core (WebSocket)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"}`}></span>
          <span className={`text-xs ${isConnected ? "text-emerald-400" : "text-red-400"}`}>
            {isConnected ? "Live" : "Offline"}
          </span>
        </div>
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