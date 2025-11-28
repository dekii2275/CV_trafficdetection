import cv2
import yt_dlp

# Cấu hình kích thước (BẮT BUỘC PHẢI KHỚP VỚI BACKEND)
PROCESS_WIDTH = 480
PROCESS_HEIGHT = 270

VIDEO_URLS = [
    'https://www.youtube.com/live/CaMkzNXwVcE', # Camera 0
    'https://www.youtube.com/live/xCNRP131kNY', # Camera 1
]

def get_stream_url(youtube_url):
    ydl_opts = {"quiet": True, "format": "best[height<=360]", "nocheckcertificate": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return info.get("url", youtube_url)
    except: return youtube_url

if __name__ == "__main__":
    for i, url in enumerate(VIDEO_URLS):
        print(f"📸 Đang chụp Camera {i}...")
        
        cap = cv2.VideoCapture(get_stream_url(url))
        
        if cap.isOpened():
            # Đọc đúng 1 frame
            ret, frame = cap.read()
            
            if ret:
                # Resize về chuẩn 480x270
                frame = cv2.resize(frame, (PROCESS_WIDTH, PROCESS_HEIGHT))
                
                # Lưu ra file để bạn mở bằng Paint lấy tọa độ cho dễ
                filename = f"snapshot_cam_{i}.jpg"
                cv2.imwrite(filename, frame)
                print(f"✅ Đã lưu ảnh: {filename}")
                
                # Hiển thị lên xem thử
                cv2.imshow(f"Camera {i}", frame)
                cv2.waitKey(1000) # Hiện 1 giây rồi tự tắt
            
            cap.release()
        else:
            print(f"❌ Lỗi mở Camera {i}")

    cv2.destroyAllWindows()
    print("👋 Xong. Hãy mở file ảnh .jpg vừa tạo để lấy tọa độ ROI.")