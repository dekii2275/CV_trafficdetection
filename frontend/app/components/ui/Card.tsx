import type { ReactNode } from "react";

interface CardProps {
    children: ReactNode;
}

export default function Card({ children }: CardProps) {
    return <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4 shadow-xl">{children}</div>;
}
