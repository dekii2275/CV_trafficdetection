import type { ChartPoint } from "../../lib/types";

interface VehicleLineChartProps {
    points: ChartPoint[];
}

export default function VehicleLineChart({ points }: VehicleLineChartProps) {
    const maxValue = Math.max(...points.map((point) => point.value));

    return (
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
    );
}
