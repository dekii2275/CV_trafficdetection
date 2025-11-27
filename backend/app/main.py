import os
import sys
import signal
from fastapi import FastAPI
from app.api import state
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from app.db.base import create_tables
from app.core.config import settings_network
from app.api import api_vehicles, api_chatbot, chat_history
from app.services.road_services.AnalyzeOnRoad import AnalyzeOnRoad

os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_DSHOW"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


app = FastAPI(
    title="Smart Transportation System API",
    description="""
    Real-time Traffic Monitoring & AI Assistant
    
    API cung cấp:
    - Real-time video streaming và phân tích giao thông
    - AI Chatbot hỗ trợ thông tin giao thông
    - Analytics và metrics về lưu lượng xe
    
    """,
    version="1.0.0",
    docs_url="/docs",  
    redoc_url="/redoc", 
    contact={
        "name": "Lê Việt Anh",
        "email": "levietanhtrump@gmail.com",
    },
    
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def signal_handler(signum, frame):
    """Xử lý Ctrl+C"""
    print("\nĐang shutdown server...")
    if state.analyzer:
        state.analyzer.cleanup_processes()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.on_event("startup")
async def startup_event():
    """Tạo bảng database khi khởi động"""
    print("Creating database tables...")
    try:
        await create_tables()
        print("Tạo xong bảng database.")
    except Exception as e:
        print(f"Lỗi tạo bảng database: {e}")
        raise e

@app.on_event("shutdown")
def shutdown():
    print("Tắt mọi thứ...")
    if state.analyzer:
        state.analyzer.cleanup_processes()

@app.get(
    path='/',
    tags=["Root"],
    summary="Redirect to Frontend",
    description="Redirect người dùng đến trang Frontend"
)
def direct_home():
    return RedirectResponse(url= settings_network.URL_FRONTEND)

app.include_router(
    router= api_vehicles.router, 
    prefix="/api/v1", 
    tags=["Traffic Monitoring"],
)
app.include_router(
    router= api_chatbot.router, 
    prefix="/api/v1", 
    tags=["AI Chatbot"],
)
app.include_router(
    router=chat_history.router,
    prefix="/api/v1/chat",
    tags=["Chat History"],
)

