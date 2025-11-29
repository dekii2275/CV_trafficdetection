import cv2
import numpy as np
import yt_dlp
from pathlib import Path

# ⚠️ CẤU HÌNH ĐÚNG KÍCH THƯỚC BACKEND ĐANG CHẠY
# (Phải khớp với process_width/height trong AnalyzeOnRoadBase.py)
PROCESS_WIDTH = 854
PROCESS_HEIGHT = 480

# Danh sách link video (Copy từ config của bạn)
VIDEO_URLS = [
    'https://www.youtube.com/live/CaMkzNXwVcE', # Camera 0
    'https://www.youtube.com/live/xCNRP131kNY', # Camera 1
]

def get_stream_url(youtube_url):
    """Lấy link stream (Có hỗ trợ Cookies nếu có file)"""
    try:
        base_dir = Path(__file__).parent
        cookie_path = base_dir / "cookies.txt"
    except:
        cookie_path = Path("cookies.txt")

    ydl_opts = {
        "quiet": True, "no_warnings": True,
        "format": "best[height<=720]",  # Lấy nguồn nét để resize xuống cho đẹp
        "nocheckcertificate": True,
        "cookiefile": str(cookie_path) if cookie_path.exists() else None,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if info and "url" in info: return info["url"]
    except Exception as e:
        print(f"Lỗi lấy link: {e}")
    return youtube_url

# Biến lưu các điểm đang vẽ
points = []

def mouse_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        # Khi click chuột trái, thêm điểm vào danh sách
        points.append([x, y])
        print(f"📍 Điểm {len(points)}: [{x}, {y}]")
        
        # Vẽ điểm đó lên hình để dễ nhìn
        cv2.circle(param, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("ROI Config Tool", param)

if __name__ == "__main__":
    print(f"🚀 TOOL VẼ ROI (Độ phân giải chuẩn: {PROCESS_WIDTH}x{PROCESS_HEIGHT})")
    print("-" * 50)
    print("👉 HƯỚNG DẪN:")
    print("1. Click chuột trái lên ảnh để chọn các điểm bao quanh mặt đường.")
    print("2. Sau khi chọn xong 4-5 điểm, NHÌN VÀO TERMINAL để copy mảng tọa độ.")
    print("3. Bấm phím 'n' để chuyển sang Camera tiếp theo.")
    print("4. Bấm phím 'q' để thoát.")
    print("-" * 50)

    for i, url in enumerate(VIDEO_URLS):
        print(f"\n🎥 Đang tải Camera {i}...")
        points = [] # Reset điểm cho cam mới
        
        stream_url = get_stream_url(url)
        cap = cv2.VideoCapture(stream_url)

        if not cap.isOpened():
            print(f"❌ Không mở được Camera {i}")
            continue

        # Đọc 1 frame
        ret, frame = cap.read()
        cap.release()

        if ret:
            # Resize về đúng kích thước Backend đang xử lý
            frame = cv2.resize(frame, (PROCESS_WIDTH, PROCESS_HEIGHT))
            
            # Hiển thị cửa sổ
            cv2.namedWindow("ROI Config Tool")
            cv2.setMouseCallback("ROI Config Tool", mouse_click, frame)
            cv2.imshow("ROI Config Tool", frame)
            
            # Chờ phím bấm
            while True:
                key = cv2.waitKey(1) & 0xFF
                if key == ord('n'): # Next
                    # In ra kết quả cuối cùng để copy
                    print(f"\n✅ COPY DÒNG DƯỚI VÀO CONFIG (Camera {i}):")
                    print(f"np.array({points})")
                    break
                if key == ord('q'): # Quit
                    cv2.destroyAllWindows()
                    exit()
        else:
            print("⚠️ Không đọc được hình ảnh.")

    cv2.destroyAllWindows()