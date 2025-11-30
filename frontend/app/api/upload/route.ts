import { NextResponse } from "next/server";

export async function POST(request: Request) {
    const formData = await request.formData();
    const file = formData.get("file"); // Lấy file từ form

    if (!file) {
        return NextResponse.json({ error: "Missing file" }, { status: 400 });
    }

    // upload file lên backend
    return NextResponse.json({ success: true });
}
