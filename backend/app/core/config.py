import os
from dotenv import load_dotenv
import numpy as np
from pathlib import Path

# Load env từ file .env ở thư mục backend
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class SettingServer:
    # Có thể giữ lại hoặc để trống nếu bỏ tính năng login, 
    # nhưng nên giữ PROJECT_NAME và DATABASE_URL phòng khi Chatbot cần lưu lịch sử
    PROJECT_NAME = "Smart Traffic Monitoring"
    DATABASE_URL = os.getenv("DATABASE_URL") 
    # Các phần JWT dưới đây có thể bỏ qua nếu không dùng auth
    # JWT_SECRET = os.getenv("JWT_SECRET_KEY", "secret_for_test")
    # JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    # ACCESS_TOKEN_EXPIRE_DAYS = 30

class SettingMetricTransport:
    # 1. Cấu hình Vùng (ROI)
    # Vì video YouTube mới chưa biết góc quay, tôi để tạm 1 vùng mặc định.
    # Bạn CẦN chỉnh lại toạ độ này sau khi chạy lần đầu.
    REGIONS = [
        np.array([[6, 542], [864, 279], [1192, 296], [968, 713], [3, 709]])
    ]


    # 2. Cấu hình Video YouTube
    PATH_VIDEOS = [
        'https://www.youtube.com/live/CaMkzNXwVcE?si=w_jYUgjXNIeXqKQx'
    ]

    # 3. Tỷ lệ mét/pixel
    # Cần map 1-1 với số lượng video. Vì có 1 video nên để 1 giá trị.
    # Bạn cần ước lượng lại giá trị này cho video mới.
    METER_PER_PIXELS = [
        0.015
    ]

    # 4. Đường dẫn Model
    # Tính toán đường dẫn tuyệt đối để tránh lỗi "File not found"
    # Logic: Từ file config.py đi ngược ra root project -> vào folder models
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent # Ra đến thư mục project_name
    MODELS_PATH = os.path.join(BASE_DIR, 'models', 'traffic_best_new.pt')

    # Chuyển sang 'cuda' nếu máy bạn có GPU NVIDIA, nếu không thì để 'cpu'
    DEVICE = 'cpu' 

class SettingChatBot:
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Đảm bảo file .env có GOOGLE_API_KEY
    LLM = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.6, 
        max_output_tokens=1024
    )

class SettingNetwork:
    BASE_URL_API = "http://localhost:8000"
    URL_FRONTEND = "http://localhost:5173"

# Khởi tạo settings
settings_server = SettingServer()
settings_metric_transport = SettingMetricTransport()
settings_chat_bot = SettingChatBot()
settings_network = SettingNetwork()

# Traffic Thresholds (Giữ nguyên hoặc update theo tên video YouTube nếu cần)
# Vì tên video YouTube dài và dynamic, bạn nên map theo index hoặc đặt một key chung.
from typing import Dict, TypedDict

class RoadThreshold(TypedDict):
    v: int
    c1: int
    c2: int

# Bạn có thể thêm key là URL hoặc tên đại diện video vào đây
TRAFFIC_THRESHOLDS: Dict[str, RoadThreshold] = {
    "Default": {"v": 15, "c1": 15, "c2": 25},
    # Mapping tạm thời nếu script lấy tên video từ URL
    "CaMkzNXwVcE": {"v": 15, "c1": 20, "c2": 30} 
}

DEFAULT_THRESHOLD: RoadThreshold = {"v": 15, "c1": 15, "c2": 25}

def get_threshold_for_road(road_name: str) -> RoadThreshold:
    # Logic fallback: Nếu không tìm thấy tên đường, trả về Default
    for key in TRAFFIC_THRESHOLDS:
        if key in road_name:
            return TRAFFIC_THRESHOLDS[key]
    return DEFAULT_THRESHOLD