import { calculatePercentage, formatNumber } from "../../lib/utils";

interface CounterChartProps {
    data: Array<{ label: string; value: number }>;
}

const colors = ["bg-emerald-400", "bg-sky-400", "bg-amber-400", "bg-violet-400"];

export default function RealtimeCounterChart({ data }: CounterChartProps) {
    const total = data.reduce((sum, item) => sum + item.value, 0);

    return (
        <div className="space-y-3">
            {data.map((item, index) => {
                const percent = calculatePercentage(item.value, total);

                return (
                    <div key={item.label}>
                        <div className="mb-1 flex justify-between text-xs text-slate-400">
                            <span>{item.label}</span>
                            <span>
                                {formatNumber(item.value)} · {percent}%
                            </span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-800">
                            <div
                                className={`h-full rounded-full ${colors[index % colors.length]}`}
                                style={{ width: `${percent}%` }}
                            />
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
