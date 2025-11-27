import { NextResponse } from "next/server";

export async function GET() {
    // Proxy video stream from backend or mock data
    return NextResponse.json({
        streamUrl: "https://example.com/live/stream.m3u8",
    });
}
