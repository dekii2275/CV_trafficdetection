import os
from dotenv import load_dotenv
from pathlib import Path
import numpy as np
from typing import TypedDict, Dict
import torch

# ============================================================
# 1. CẤU HÌNH CƠ BẢN & ĐƯỜNG DẪN GỐC
# ============================================================
# Tìm thư mục gốc project (CV_trafficdetection)
# Giả sử file này nằm ở: backend/app/core/config.py -> parent x4 là đúng về root
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Debug
print(f"🔍 Looking for .env at: {env_path}")
print(f"📁 .env exists: {env_path.exists()}")

class SettingServer:
    PROJECT_NAME = "Smart Traffic Monitoring"
    # Dùng BASE_DIR để trỏ db file chính xác
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/data/chat.db")

class SettingMetricTransport:
    """Traffic monitoring configuration"""
    # 1. Cấu hình Vùng (ROI)
    REGIONS = [
        np.array([[2, 351], [486, 357], [586, 133], [391, 119], [7, 225]]),
        np.array([[2, 217], [309, 94], [415, 95], [225, 357], [2, 355]])
    ]
    
    # 2. Cấu hình Video YouTube (Lưu ý: Link Live có thể chết, cần update thường xuyên)
    PATH_VIDEOS = [
        'https://www.youtube.com/live/CaMkzNXwVcE',
        'https://www.youtube.com/live/xCNRP131kNY'
    ]
    
    METER_PER_PIXELS = [0.015]
    
    # 4. Đường dẫn Model (Sử dụng global BASE_DIR)
    MODELS_PATH = str(BASE_DIR / 'models' / 'best.pt')
    
    DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

class SettingChatBot:
    """Chatbot RAG configuration"""
    # API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.6"))
    MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", "1024"))
    
    # --- CẤU HÌNH ĐƯỜNG DẪN DỮ LIỆU (QUAN TRỌNG) ---
    # 1. Định nghĩa thư mục data nằm trong BASE_DIR
    _DATA_DIR = BASE_DIR / "data"

    # 2. Hardcode đường dẫn (Bỏ os.getenv để tránh lỗi từ file .env)
    LAW_DOCUMENTS_PATH: str = str(_DATA_DIR / "law_documents")
    VECTOR_DB_PATH: str = str(_DATA_DIR / "chroma_db")
    
    VECTOR_COLLECTION_NAME: str = os.getenv("VECTOR_COLLECTION_NAME", "traffic_laws")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "keepitreal/vietnamese-sbert")
    
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    
    @staticmethod
    def get_llm():
        if not SettingChatBot.GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY not found in .env file")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=SettingChatBot.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=SettingChatBot.MODEL_NAME,
                generation_config={
                    "temperature": SettingChatBot.TEMPERATURE,
                    "max_output_tokens": SettingChatBot.MAX_TOKENS,
                }
            )
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini model: {e}")
    
    @staticmethod
    def validate_config():
        errors = []
        if not SettingChatBot.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is missing")
        
        # Kiểm tra đường dẫn tồn tại
        if not Path(SettingChatBot.LAW_DOCUMENTS_PATH).exists():
            # Tự động tạo thư mục nếu chưa có (Tiện ích bổ sung)
            try:
                Path(SettingChatBot.LAW_DOCUMENTS_PATH).mkdir(parents=True, exist_ok=True)
                print(f"📁 Created missing directory: {SettingChatBot.LAW_DOCUMENTS_PATH}")
            except:
                errors.append(f"LAW_DOCUMENTS_PATH does not exist: {SettingChatBot.LAW_DOCUMENTS_PATH}")
        
        if errors:
            print("⚠️  Configuration warnings:", errors)
        return len(errors) == 0

class SettingNetwork:
    BASE_URL_API = os.getenv("BASE_URL_API", "http://localhost:8000")
    URL_FRONTEND = os.getenv("URL_FRONTEND", "http://localhost:5173")
    ALLOWED_ORIGINS = [URL_FRONTEND, "http://localhost:3000", "http://localhost:5173", "http://localhost:8080"]

# Traffic Thresholds & Singleton Instances
class RoadThreshold(TypedDict):
    v: int; c1: int; c2: int

TRAFFIC_THRESHOLDS: Dict[str, RoadThreshold] = {
    "Default": {"v": 15, "c1": 15, "c2": 25},
    "CaMkzNXwVcE": {"v": 15, "c1": 20, "c2": 30}
}
DEFAULT_THRESHOLD: RoadThreshold = {"v": 15, "c1": 15, "c2": 25}

def get_threshold_for_road(road_name: str) -> RoadThreshold:
    for key in TRAFFIC_THRESHOLDS:
        if key in road_name: return TRAFFIC_THRESHOLDS[key]
    return DEFAULT_THRESHOLD

settings_server = SettingServer()
settings_metric_transport = SettingMetricTransport()
settings_chat_bot = SettingChatBot()
settings_network = SettingNetwork()

try:
    SettingChatBot.validate_config()
except Exception as e:
    print(f"⚠️ Config Warning: {e}")