import { NextResponse } from "next/server";

export async function GET() {
    const points = Array.from({ length: 12 }).map((_, idx) => ({
        label: `${idx + 1}:00`,
        value: Math.floor(Math.random() * 400) + 100,
    }));

    return NextResponse.json(points);
}
