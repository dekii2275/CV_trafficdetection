import os
from dotenv import load_dotenv
from pathlib import Path
import numpy as np
from typing import TypedDict, Dict
import torch

# ============================================================
# 1. CẤU HÌNH CƠ BẢN & ĐƯỜNG DẪN GỐC
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

print(f"🔍 Looking for .env at: {env_path}")
print(f"📁 .env exists: {env_path.exists()}")

class SettingServer:
    PROJECT_NAME = "Smart Traffic Monitoring"
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/data/chat.db")

class SettingMetricTransport:
    """
    Traffic monitoring configuration
    ⚠️ ĐÃ GIẢM XUỐNG CÒN 2 CAMERA ĐỂ TỐI ƯU TỐC ĐỘ
    """
    
    # ===== SỐ CAMERAS (Chỉ chạy 2 cái) =====
    NUM_CAMERAS = 2 
    
    # ===== 1. ROI REGIONS (Giữ lại 2 vùng tương ứng) =====
    REGIONS = [
        # Camera 0: Phuong Tran
        np.array([[1, 354], [1, 478], [629, 476], [776, 171], [628, 160], [4, 357]]),
        
        # Camera 1: Nguyen Hieu  
        np.array([[0,277], [484, 105], [570,110], [299, 477], [4, 474]]),
    ]
    
    # ===== 2. VIDEO URLS (Giữ lại 2 link) =====
    PATH_VIDEOS = [
        'https://www.youtube.com/live/CaMkzNXwVcE',     # Camera 0
        'https://www.youtube.com/live/xCNRP131kNY',     # Camera 1
    ]
    
    # ===== 3. METER PER PIXEL (Giữ lại 2 số) =====
    METER_PER_PIXELS = [
        0.015,  # Camera 0
        0.015,  # Camera 1
    ]
    
    # ===== 4. MODEL PATH =====
    # Lưu ý: Nên dùng 'yolov8n.pt' gốc để test tốc độ trước khi dùng 'best.pt'
    MODELS_PATH = str(BASE_DIR / 'models' / 'best.pt')
    
    # ===== 5. DEVICE CONFIGURATION =====
    # Tự động chọn GPU nếu có, nếu không thì dùng CPU
    DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    @classmethod
    def validate(cls):
        errors = []
        num_videos = len(cls.PATH_VIDEOS)
        num_regions = len(cls.REGIONS)
        
        if num_videos != num_regions:
            errors.append(f"Mismatch: {num_videos} Videos vs {num_regions} Regions")
        
        if not Path(cls.MODELS_PATH).exists():
            # Fallback về yolov8n chuẩn nếu không tìm thấy model custom
            print(f"⚠️ Custom model not found. Falling back to yolov8n.pt")
            cls.MODELS_PATH = "yolov8n.pt" 
        
        if errors:
            print("❌ Config Errors:", errors)
            return False
        
        print(f"✅ Config validated: {num_videos} cameras ready (Device: {cls.DEVICE})")
        return True
    
    @classmethod
    def get_available_cameras(cls):
        return min(len(cls.PATH_VIDEOS), len(cls.REGIONS))


class SettingChatBot:
    """Chatbot RAG configuration"""
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.6"))
    MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", "1024"))
    
    _DATA_DIR = BASE_DIR / "data"
    LAW_DOCUMENTS_PATH: str = str(_DATA_DIR / "law_documents")
    VECTOR_DB_PATH: str = str(_DATA_DIR / "chroma_db")
    VECTOR_COLLECTION_NAME: str = "traffic_laws"
    EMBEDDING_MODEL: str = "keepitreal/vietnamese-sbert"
    
    @staticmethod
    def validate_config():
        return True # Bỏ qua validate chatbot để tập trung fix cam


class SettingNetwork:
    BASE_URL_API = os.getenv("BASE_URL_API", "http://localhost:8000")
    URL_FRONTEND = os.getenv("URL_FRONTEND", "http://localhost:5173")
    ALLOWED_ORIGINS = ["*"] # Mở rộng để dễ debug


# Traffic Thresholds
TRAFFIC_THRESHOLDS: Dict[str, dict] = {
    "Default": {"v": 15, "c1": 15, "c2": 25},
}

def get_threshold_for_road(road_name: str):
    return TRAFFIC_THRESHOLDS.get("Default")


# ============================================================
# SINGLETON INSTANCES
# ============================================================
settings_server = SettingServer()
settings_metric_transport = SettingMetricTransport()
settings_chat_bot = SettingChatBot()
settings_network = SettingNetwork()

# Validate ngay khi import
try:
    if not SettingMetricTransport.validate():
        print("⚠️ Transport config invalid")
except Exception as e:
    print(f"⚠️ Config warning: {e}")