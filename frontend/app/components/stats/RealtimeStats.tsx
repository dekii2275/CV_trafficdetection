import Card from "../ui/Card";
import StatCard from "./StatCard";
import { formatCompactNumber, formatNumber, formatRatePerMinute } from "../../lib/utils";

const liveStats = {
    total: 18420,
    ratePerMinute: 328,
    breakdown: {
        car: 12140,
        truck: 3820,
        bike: 1840,
        bus: 620,
    },
};

const summaryCards = [
    {
        label: "Tổng lượt hôm nay",
        value: formatNumber(liveStats.total),
        helperText: "Tính từ 00:00",
        trend: 3.4,
    },
    {
        label: "Tốc độ đếm hiện tại",
        value: formatRatePerMinute(liveStats.ratePerMinute),
        helperText: "Trung bình 5 phút",
        trend: 1.2,
    },
];

export default function RealtimeStats() {
    const breakdownCards = Object.entries(liveStats.breakdown).map(([label, value]) => ({
        label: `Lượt ${label}`,
        value: formatCompactNumber(value),
        helperText: "Trong 1 giờ",
    }));

    return (
        <Card>
            <div className="mb-6 flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold">Realtime Vehicle Count</h2>
                    <p className="text-sm text-slate-400">Chỉ tập trung vào thống kê phương tiện</p>
                </div>
                <span className="text-xs text-emerald-400">Live</span>
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
