import os
from dotenv import load_dotenv
import numpy as np

load_dotenv()


class SettingServer:
    PROJECT_NAME = "FastAPI CRUD with JWT"
    DATABASE_URL = os.getenv("DATABASE_URL")
    JWT_SECRET = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS"))


class SettingMetricTransport:
    REGIONS = [
        np.array([[50, 400], [50, 265], [370, 130], [540, 130], [490, 400]]),
        np.array([[230, 400], [90, 260], [350, 200], [600, 320], [600, 400]]),
        np.array([[50, 400], [50, 340], [400, 125], [530, 185], [470, 400]]),
        np.array([[140, 400], [400, 200], [550, 200], [530, 400]]),
        np.array([[50, 400], [50, 320], [390, 130], [550, 220], [480, 400]]),
    ]

    PATH_VIDEOS = [
        "./video_test/Văn Quán.mp4",
        "./video_test/Văn Phú.mp4",
        "./video_test/Nguyễn Trãi.mp4",
        "./video_test/Ngã Tư Sở.mp4",
        "./video_test/Đường Láng.mp4",
    ]

    METER_PER_PIXELS = [
        0.1,
        0.15,
        0.42,
        0.15,
        0.05
    ]
    MODELS_PATH = r'./ai_models/model N/openvino models/best_int8_openvino_model'

    DEVICE = 'cpu'


class SettingChatBot:
    from langchain_google_genai import ChatGoogleGenerativeAI

    LLM = ChatGoogleGenerativeAI(model="gemini-2.5-flash",
                                 temperature=0.6,
                                 max_output_tokens=1024
                                 )
    # Dùng ollama local api llm

    # from langchain_openai import OpenAI
    # LLM = OpenAI(model_name="gemma3:4b",
    #              temperature=0.6,
    #              max_tokens=1024)


class SettingNetwork:
    BASE_URL_API = "http://localhost:8000"
    URL_FRONTEND = "http://localhost:5173"


settings_server = SettingServer()
settings_metric_transport = SettingMetricTransport()
settings_chat_bot = SettingChatBot()
settings_network = SettingNetwork()
setting_chatbot = SettingChatBot()

# ================= Traffic Thresholds (per-road) =================
# v: average speed threshold (km/h) - >= v => fast, else slow
# c1: vehicle count threshold for busy
# c2: vehicle count threshold for congested

from typing import Dict, TypedDict


class RoadThreshold(TypedDict):
    v: int
    c1: int
    c2: int


TRAFFIC_THRESHOLDS: Dict[str, RoadThreshold] = {
    "Đường Láng": {"v": 13, "c1": 17, "c2": 26},
    "Ngã Tư Sở": {"v": 17, "c1": 45, "c2": 57},
    "Nguyễn Trãi": {"v": 30, "c1": 25, "c2": 35},
    "Văn Quán": {"v": 10, "c1": 10, "c2": 17},
    "Văn Phú": {"v": 15, "c1": 18, "c2": 26},
}

DEFAULT_THRESHOLD: RoadThreshold = {"v": 15, "c1": 15, "c2": 25}


def get_threshold_for_road(road_name: str) -> RoadThreshold:
    return TRAFFIC_THRESHOLDS.get(road_name, DEFAULT_THRESHOLD)