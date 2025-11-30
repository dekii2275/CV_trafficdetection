import { NextResponse } from "next/server";

// API trả về URL stream video
export async function GET() {
    return NextResponse.json({
        streamUrl: "https://example.com/live/stream.m3u8",
    });
}
