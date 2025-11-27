interface StatCardProps {
    label: string;
    value: string | number;
    helperText?: string;
    trend?: number;
}

export default function StatCard({ label, value, helperText, trend }: StatCardProps) {
    const trendColor = trend && trend >= 0 ? "text-emerald-400" : "text-rose-400";
    const formattedTrend = typeof trend === "number" ? `${trend > 0 ? "+" : ""}${trend.toFixed(1)}%` : null;

    return (
        <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
            <div className="flex items-baseline gap-2">
                <span className="text-2xl font-semibold">{value}</span>
                {formattedTrend && <span className={`text-xs ${trendColor}`}>{formattedTrend}</span>}
            </div>
            {helperText && <p className="text-xs text-slate-500">{helperText}</p>}
        </div>
    );
}
