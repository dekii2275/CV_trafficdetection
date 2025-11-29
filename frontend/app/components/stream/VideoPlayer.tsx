"use client";

import { useEffect, useRef, useState } from "react";

// ==================================================================================
// 1. CẤU HÌNH DANH SÁCH CAMERA (GIẢM CÒN 2 CAM)
// ==================================================================================
const CAMERAS = [
  { id: "0", name: "Camera 0 - Cổng Chính", wsUrl: "ws://localhost:8000" },
  { id: "1", name: "Camera 1 - Ngã Tư A",   wsUrl: "ws://localhost:8000" },
  // Đã ẩn bớt 2 camera dưới để giảm tải
  // { id: "2", name: "Camera 2 - Ngã Tư B",   wsUrl: "ws://localhost:8000" },
  // { id: "3", name: "Camera 3 - Bãi Đỗ Xe",  wsUrl: "ws://localhost:8000" },
];

// ==================================================================================
// 2. COMPONENT CHÍNH: VIDEO PLAYER (Default Export)
// ==================================================================================
interface VideoPlayerProps {
  roadName?: string;
  backendUrl?: string;
  label?: string; 
}

export default function VideoPlayer({ 
  roadName = "0", 
  backendUrl = "ws://localhost:8000",
  label
}: VideoPlayerProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const wsUrl = `${backendUrl}/api/v1/ws/frames/${roadName}`;
    
    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          if (event.data instanceof Blob) {
            const url = URL.createObjectURL(event.data);
            if (imgRef.current) {
              if (imgRef.current.src.startsWith('blob:')) {
                URL.revokeObjectURL(imgRef.current.src);
              }
              imgRef.current.src = url;
            }
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          if (wsRef.current?.readyState !== 1) {
             setTimeout(connectWebSocket, 3000);
          }
        };

        ws.onerror = (e) => {
          console.error("WebSocket Error:", e);
          setError("Lỗi kết nối");
        };
      } catch (err) {
        setError("Không thể khởi tạo");
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (imgRef.current?.src.startsWith('blob:')) {
        URL.revokeObjectURL(imgRef.current.src);
      }
    };
  }, [roadName, backendUrl]); // ✅ Đã bỏ label khỏi dependency array

  return (
    <div className="relative w-full h-full bg-slate-900 rounded-lg overflow-hidden border border-slate-700 shadow-md flex flex-col group">
      <div className="absolute top-2 left-2 z-10 bg-black/60 backdrop-blur-sm px-2 py-1 rounded text-xs text-white font-mono flex items-center gap-2 border border-white/10">
        <span className={`relative flex h-2 w-2`}>
          {isConnected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
        </span>
        {label || `CAM ${roadName}`}
      </div>

      <div className="flex-1 relative flex items-center justify-center bg-black">
        {error ? (
          <div className="flex flex-col items-center gap-2 text-red-400 text-sm px-4">
            <span className="text-2xl">⚠️</span>
            <p>{error}</p>
          </div>
        ) : (
          <>
            <img
              ref={imgRef}
              className="w-full h-full object-contain" 
              alt={`Stream ${roadName}`}
              style={{ display: isConnected ? 'block' : 'none' }}
            />
            {!isConnected && !error && (
              <div className="flex flex-col items-center gap-3">
                <div className="animate-spin w-8 h-8 border-4 border-slate-700 border-t-blue-500 rounded-full"></div>
                <span className="text-slate-500 text-xs animate-pulse">Connecting...</span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ==================================================================================
// 3. COMPONENT PHỤ: MULTI CAMERA GRID (Named Export)
// ==================================================================================
export function MultiCameraGrid() {
  return (
    <div className="w-full p-4 bg-slate-950 rounded-xl border border-slate-800 shadow-2xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          🎥 Traffic Monitor System
          <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-1 rounded-full">
            2 Cameras View
          </span>
        </h2>
        <div className="flex gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span className="text-xs text-slate-400">System Online</span>
        </div>
      </div>

      {/* - h-[50vh]: Giảm chiều cao tổng xuống một chút vì chỉ có 1 hàng 
         - md:grid-cols-2: Trên máy tính sẽ chia 2 cột (mỗi cam 1 bên)
         - grid-cols-1: Trên điện thoại sẽ xếp chồng lên nhau
      */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full h-[50vh] min-h-[400px]">
        {CAMERAS.map((cam) => (
          <div key={cam.id} className="w-full h-full">
            <VideoPlayer 
              roadName={cam.id} 
              label={cam.name} 
              backendUrl={cam.wsUrl} 
            />
          </div>
        ))}
      </div>
    </div>
  );
}