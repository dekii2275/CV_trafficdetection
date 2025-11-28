"use client";

import { useEffect, useRef, useState } from "react";

interface VideoPlayerProps {
  roadName?: string;
  backendUrl?: string;
}

export default function VideoPlayer({ 
  roadName = "default", 
  backendUrl = "ws://localhost:8000" 
}: VideoPlayerProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        // Tạo kết nối WebSocket
        const ws = new WebSocket(`${backendUrl}/api/v1/ws/frames/${roadName}`);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log("✅ WebSocket video stream connected");
          setIsConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          // Nhận frame bytes từ backend
          if (event.data instanceof Blob) {
            const url = URL.createObjectURL(event.data);
            if (imgRef.current) {
              // Giải phóng URL cũ để tránh memory leak
              if (imgRef.current.src.startsWith('blob:')) {
                URL.revokeObjectURL(imgRef.current.src);
              }
              imgRef.current.src = url;
            }
          }
        };

        ws.onclose = (event) => {
          console.log("🔌 WebSocket video stream disconnected:", event.code);
          setIsConnected(false);
          
          // Tự động reconnect sau 3 giây
          if (event.code !== 1000) { // 1000 = normal closure
            setTimeout(connectWebSocket, 3000);
          }
        };

        ws.onerror = (error) => {
          console.error("❌ WebSocket video error:", error);
          setError("Kết nối video stream bị lỗi");
        };

      } catch (err) {
        console.error("❌ WebSocket connection error:", err);
        setError("Không thể kết nối đến video stream");
      }
    };

    connectWebSocket();

    // Cleanup khi component unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000); // Normal closure
      }
      // Giải phóng blob URL
      if (imgRef.current?.src.startsWith('blob:')) {
        URL.revokeObjectURL(imgRef.current.src);
      }
    };
  }, [roadName, backendUrl]);

  return (
    <div className="aspect-video rounded-xl bg-slate-800 p-4 shadow-lg relative">
      {error ? (
        <div className="flex h-full items-center justify-center text-red-400">
          <div className="text-center">
            <p>{error}</p>
            <p className="text-sm text-slate-500 mt-2">
              Kiểm tra kết nối backend tại {backendUrl}
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Status indicator */}
          <div className="absolute top-6 right-6 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-400' : 'bg-red-400'
            }`}></div>
            <span className="text-xs text-slate-400">
              {isConnected ? 'LIVE' : 'CONNECTING...'}
            </span>
          </div>

          {/* Video frame */}
          <img
            ref={imgRef}
            className="w-full h-full object-contain rounded-lg"
            alt="Traffic Video Stream"
            style={{ display: isConnected ? 'block' : 'none' }}
          />

          {/* Loading placeholder */}
          {!isConnected && !error && (
            <div className="flex h-full items-center justify-center text-slate-400">
              <div className="text-center">
                <div className="animate-spin w-8 h-8 border-2 border-slate-600 border-t-blue-500 rounded-full mx-auto mb-4"></div>
                <p>Đang kết nối video stream...</p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}