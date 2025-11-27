import { NextResponse } from "next/server";

export async function POST(request: Request) {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!file) {
        return NextResponse.json({ error: "Missing file" }, { status: 400 });
    }

    // TODO: send to backend storage
    return NextResponse.json({ success: true });
}
