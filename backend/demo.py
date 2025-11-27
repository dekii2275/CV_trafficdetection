import cv2
import yt_dlp

def get_stream_url(youtube_url):
    ydl_opts = {
        "quiet": True,
        "format": "best"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info.get("url")

# ==== CONFIG ====
YOUTUBE_LINK = "https://www.youtube.com/watch?v=xCNRP131kNYx"
OUTPUT_FILE = "1.jpg"
# ================

print("🔍 Đang lấy stream URL...")
stream_url = get_stream_url(YOUTUBE_LINK)

cam = cv2.VideoCapture(stream_url)

if not cam.isOpened():
    print("❌ Không mở được stream YouTube")
    exit()

print("📸 Đang chụp 1 frame...")

ret, frame = cam.read()
cam.release()

if not ret:
    print("❌ Không đọc được frame từ livestream")
    exit()

# Resize đúng kích thước YOLO xử lý
frame_resized = cv2.resize(frame, (640, 360))

# Lưu ảnh
cv2.imwrite(OUTPUT_FILE, frame_resized)

print(f"✅ Đã lưu ảnh: {OUTPUT_FILE}")
