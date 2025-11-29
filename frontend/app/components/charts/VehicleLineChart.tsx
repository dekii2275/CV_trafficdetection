"use client";

import { useEffect, useState } from "react";
import type { ChartPoint } from "../../lib/types";
import Card from "../ui/Card";

interface VehicleLineChartProps {
    cameraId: number;
}

export default function VehicleLineChart({ cameraId }: VehicleLineChartProps) {
    const [points, setPoints] = useState<ChartPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
                const res = await fetch(`${API_BASE}/api/v1/charts/time-series/${cameraId}?hours=12`);
                
                if (res.ok) {
                    const json = await res.json();
                    if (json.points && Array.isArray(json.points)) {
                        setPoints(json.points);
                        setError(null);
                    } else if (json.message) {
                        setError(json.message);
                    }
                } else {
                    try {
                        const errorData = await res.json();
                        setError(errorData.message || errorData.error || "Không lấy được dữ liệu");
                    } catch {
                        setError(`HTTP ${res.status}: Không lấy được dữ liệu`);
                    }
                }
            } catch (e) {
                console.error("Lỗi tải biểu đồ:", e);
                setError("Lỗi kết nối");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 60000); // Refresh mỗi phút
        return () => clearInterval(interval);
    }, [cameraId]);

    if (loading) {
        return (
            <Card>
                <div className="h-48 flex items-center justify-center text-slate-400">
                    Đang tải...
                </div>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <div className="h-48 flex items-center justify-center text-yellow-400">
                    {error}
                </div>
            </Card>
        );
    }

    if (points.length === 0) {
        return (
            <Card>
                <div className="h-48 flex items-center justify-center text-slate-400">
                    Chưa có dữ liệu
                </div>
            </Card>
        );
    }

    const maxValue = Math.max(...points.map((point) => point.value), 1);

    return (
        <Card>
            <div className="mb-4">
                <h3 className="text-sm font-semibold text-slate-300">
                    Lưu lượng theo giờ • Camera {cameraId}
                </h3>
            </div>
            <div className="flex h-48 items-end gap-2 rounded-lg bg-slate-900 p-4">
                {points.map((point) => {
                    const height = maxValue === 0 ? 0 : (point.value / maxValue) * 100;
                    return (
                        <div key={point.label} className="flex flex-1 flex-col items-center gap-2">
                            <div className="w-full rounded-full bg-emerald-500" style={{ height: `${height}%` }} />
                            <span className="text-xs text-slate-400">{point.label}</span>
                        </div>
                    );
                })}
            </div>
        </Card>
    );
}