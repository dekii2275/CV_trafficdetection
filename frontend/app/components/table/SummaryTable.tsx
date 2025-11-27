import type { ReactNode } from "react";

interface SummaryTableProps {
    children: ReactNode;
}

export default function SummaryTable({ children }: SummaryTableProps) {
    return (
        <table className="w-full text-sm">
            <thead className="text-left text-slate-400">
                <tr>
                    <th className="pb-2">Camera</th>
                    <th className="pb-2">Vehicles</th>
                    <th className="pb-2">Loại chiếm đa số</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200">{children}</tbody>
        </table>
    );
}
