import type { ReactNode } from "react";
import Card from "../ui/Card";

interface ChartCardProps {
    title: string;
    children: ReactNode;
}

export default function ChartCard({ title, children }: ChartCardProps) {
    return (
        <Card>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
                {title}
            </h3>
            {children}
        </Card>
    );
}
