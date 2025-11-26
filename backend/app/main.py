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
    redoc_url="/redoc"
    
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def graceful_shutdown(signum, frame):
    print("\nĐang shutdown server ...")

    if state.analyzer:
        try:
            state.analyzer.stop_flag = True
            print("Đã yêu cầu Analyzer dừng.")
        except:
            print("Analyzer không hỗ trợ stop_flag hoặc chưa khởi tạo.")

signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)


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
    print("FastAPI shutdown...")

    if state.analyzer:
        try:
            state.analyzer.stop_flag = True
            print("Đã bật stop_flag cho Analyzer.")
        except:
            pass

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

