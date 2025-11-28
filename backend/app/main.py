import os
import sys
import multiprocessing

# =================================================================
# ⚠️ QUAN TRỌNG: CÀI ĐẶT MULTIPROCESSING NGAY ĐẦU FILE
# Phải đặt trước tất cả các import khác để tránh lỗi PyTorch/OpenCV
# =================================================================
try:
    # 'spawn' là phương thức an toàn nhất cho AI/Machine Learning process
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass  # Bỏ qua nếu đã được set trước đó

# =================================================================
# IMPORT MODULES
# =================================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

# Import DB và Config
from app.db.base import create_tables
from app.core.config import settings_network

# Import Routers
from app.api import api_vehicles, api_chatbot, chat_history

# Config môi trường cho OpenCV (tránh lỗi xung đột camera trên Windows)
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_DSHOW"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# =================================================================
# KHỞI TẠO APP
# =================================================================
app = FastAPI(
    title="Smart Transportation System API",
    description="""
    Real-time Traffic Monitoring & AI Assistant
    
    API cung cấp:
    - Real-time video streaming và phân tích giao thông (Multiprocessing)
    - AI Chatbot hỗ trợ thông tin giao thông (RAG)
    - Analytics và metrics về lưu lượng xe
    """,
    version="1.0.0",
    docs_url="/docs",  
    redoc_url="/redoc", 
    contact={
        "name": "Minh Anh - K68 Data Science",
        "email": "levietanhtrump@gmail.com",
    },
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================================================================
# EVENTS (Startup & Shutdown)
# =================================================================
@app.on_event("startup")
async def startup_event():
    """Chạy khi server bắt đầu"""
    print("🚀 Server starting up...")
    
    # 1. Tạo bảng Database
    print("Creating database tables...")
    try:
        await create_tables()
        print("✅ Database tables created.")
    except Exception as e:
        print(f"❌ Database error: {e}")
        # Không raise e để server vẫn chạy tiếp các dịch vụ khác nếu DB lỗi nhẹ

@app.on_event("shutdown")
def shutdown_event():
    """
    Chạy khi server tắt (Ctrl+C).
    Lưu ý: Các router con (api_vehicles) cũng sẽ tự kích hoạt event shutdown của riêng nó
    để tắt các process AI.
    """
    print("👋 Server shutting down...")

# =================================================================
# ROUTES
# =================================================================

@app.get(
    path='/',
    tags=["Root"],
    summary="Redirect to Frontend",
    description="Redirect người dùng đến trang Frontend"
)
def direct_home():
    return RedirectResponse(url=settings_network.URL_FRONTEND)

# Include các Router
# Lưu ý: Logic khởi tạo AI Multiprocessing nằm bên trong api_vehicles.router
# Khi include router này, các event startup/shutdown bên trong nó sẽ tự động chạy.
app.include_router(
    router=api_vehicles.router, 
    prefix="/api/v1", 
    tags=["Traffic Monitoring"],
)

app.include_router(
    router=api_chatbot.router, 
    prefix="/api/v1", 
    tags=["AI Chatbot"],
)

app.include_router(
    router=chat_history.router,
    prefix="/api/v1/chat",
    tags=["Chat History"],
)

# =================================================================
# ENTRY POINT (Dành cho việc debug trực tiếp)
# =================================================================
if __name__ == "__main__":
    import uvicorn
    # Chạy server ở chế độ debug
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)