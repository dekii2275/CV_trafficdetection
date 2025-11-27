"use client";

import { useState } from "react";

export default function Toggle() {
    const [enabled, setEnabled] = useState(true);

    return (
        <button
            onClick={() => setEnabled((prev) => !prev)}
            className={`flex h-6 w-12 items-center rounded-full px-1 transition ${
                enabled ? "bg-emerald-500" : "bg-slate-700"
            }`}
        >
            <span
                className={`h-4 w-4 rounded-full bg-white transition-transform ${
                    enabled ? "translate-x-6" : "translate-x-0"
                }`}
            />
        </button>
    );
}
