"use client";

import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import Card from "../ui/Card";

// Định nghĩa màu sắc cho từng loại xe
const COLORS = {
  car: "#10b981",   // Emerald 500
  truck: "#f59e0b", // Amber 500
  motor: "#3b82f6", // Blue 500
  bus: "#ef4444",   // Red 500
};

export default function VehicleDistributionChart() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // 🔴 FIX LỖI RECHARTS SSR: Thêm biến kiểm tra mounted
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true); // Đánh dấu đã chạy trên trình duyệt

    const fetchData = async () => {
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        
        // VehicleDistributionChart.tsx - Dòng 29-44, sửa lại:
        const res = await fetch(`${API_BASE}/api/v1/charts/vehicle-distribution`);

        if (res.ok) {
            const json = await res.json();
            
            if (json.totals) {
                const chartData = [
                    { name: "Car", value: json.totals.car || 0, color: COLORS.car },
                    { name: "Motor", value: json.totals.motor || 0, color: COLORS.motor },
                    { name: "Truck", value: json.totals.truck || 0, color: COLORS.truck },
                    { name: "Bus", value: json.totals.bus || 0, color: COLORS.bus },
                ].filter(item => item.value > 0);
                
                setData(chartData);
            }
        } else {
            // Xử lý lỗi HTTP
            try {
                const errorData = await res.json();
                console.error("Lỗi API:", errorData.message || errorData.error);
            } catch {
                console.error(`HTTP ${res.status}: Lỗi tải dữ liệu phân bố`);
            }
        }
      } catch (e) {
        console.error("Lỗi tải biểu đồ phân bố:", e);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); 
    return () => clearInterval(interval);
  }, []);

  // 🔴 FIX LỖI SSR: Chỉ render khi đã mounted
  if (!isMounted) return <Card><div className="h-[250px]" /></Card>;

  if (loading) {
    return (
      <Card>
        <div className="h-[250px] flex items-center justify-center text-slate-500 animate-pulse">
          Đang tải dữ liệu...
        </div>
      </Card>
    );
  }
  
  if (data.length === 0) {
    return (
      <Card>
        <div className="h-[250px] flex flex-col items-center justify-center text-slate-500 gap-2">
          <span className="text-2xl">📊</span>
          <p>Chưa có dữ liệu phân bố hôm nay</p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-400 uppercase">
          Phân bố phương tiện
        </h3>
        <span className="text-[10px] bg-slate-800 px-2 py-1 rounded text-slate-500">
          Hôm nay
        </span>
      </div>

      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            
            <Tooltip 
              contentStyle={{
                backgroundColor: '#1e293b', 
                borderColor: '#334155', 
                color: '#fff',
                borderRadius: '8px',
                fontSize: '12px'
              }}
              itemStyle={{color: '#fff'}}
              formatter={(value: number) => [`${value} xe`, 'Số lượng']}
            />
            
            <Legend 
              verticalAlign="bottom" 
              height={36} 
              iconType="circle"
              formatter={(value) => <span className="text-slate-300 text-xs ml-1">{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}