"use client";

interface SidebarItemProps {
    label: string;
    active?: boolean;
}

export default function SidebarItem({ label, active }: SidebarItemProps) {
    return (
        <button
            className={`w-full rounded-md px-4 py-2 text-left text-sm font-medium transition-colors ${
                active ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800"
            }`}
        >
            {label}
        </button>
    );
}
