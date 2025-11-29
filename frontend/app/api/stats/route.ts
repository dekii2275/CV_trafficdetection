import { NextResponse } from "next/server";

const MOCK_BREAKDOWN = {
    car: 1820,
    truck: 460,
    motor: 320,
    bus: 140,
};

export async function GET() {
    const now = Date.now();
    const total = Object.values(MOCK_BREAKDOWN).reduce((acc, curr) => acc + curr, 0);

    return NextResponse.json({
        timestamp: now,
        total,
        ratePerMinute: 312,
        breakdown: MOCK_BREAKDOWN,
    });
}
