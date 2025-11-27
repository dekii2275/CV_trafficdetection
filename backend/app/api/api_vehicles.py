from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse
import asyncio
import threading
from multiprocessing import Manager
import cv2
import numpy as np
import io

from app.api import state
# Import settings nếu cần dùng biến khác, nhưng analyzer tự đọc rồi
from app.services.road_services.AnalyzeOnRoad import AnalyzeOnRoad
from app.utils.transport_utils import enrich_info_with_thresholds

router = APIRouter()

# --- CẤU HÌNH GLOBAL STATE CHO DATA ---
# Chúng ta cần lưu manager dict vào state để các hàm API bên dưới có thể đọc được
if not hasattr(state, 'info_dict'):
    state.info_dict = None
if not hasattr(state, 'frame_dict'):
    state.frame_dict = None

def start_analyzer_single_thread():
    """
    Khởi tạo Analyzer chạy 1 luồng background.
    """
    if state.analyzer is not None:
        print("⚠️ Analyzer đã đang chạy rồi.")
        return

    print("🚀 Khởi tạo Analyzer (single-thread)...")

    # 1. Tạo Manager để chứa dữ liệu chia sẻ
    # Lưu vào global state để API endpoint có thể đọc
    manager = Manager()
    state.info_dict = manager.dict()
    state.frame_dict = manager.dict()

    # 2. Khởi tạo Analyzer (SỬA LẠI THAM SỐ CHO ĐÚNG CLASS MỚI)
    try:
        analyzer = AnalyzeOnRoad(
            video_index=0,              # Video đầu tiên trong config
            info_dict=state.info_dict,  # Dict để chứa số liệu
            frame_dict=state.frame_dict,# Dict để chứa ảnh
            show=False                  # False khi chạy server (không hiện cửa sổ)
        )
        state.analyzer = analyzer

        # 3. Chạy trong Thread riêng (Daemon=True để tắt khi server tắt)
        # Lưu ý: Hàm chạy chính bây giờ là process_video (của lớp cha)
        thread = threading.Thread(target=analyzer.process_video, daemon=True)
        thread.start()

        print("✅ Traffic Analyzer đã chạy trong background thread.")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo Analyzer: {e}")


@router.on_event("startup")
def startup_event():
    start_analyzer_single_thread()


# ========================== API ENDPOINTS ==========================

@router.get("/info/{road_name}")
async def get_info_road(road_name: str):
    """
    Lấy thông tin đếm xe realtime.
    Thay vì gọi hàm vào analyzer, ta đọc trực tiếp từ bộ nhớ chia sẻ (info_dict).
    """
    if state.info_dict is None:
        return JSONResponse({"error": "Analyzer chưa khởi động"}, status_code=500)

    # Convert ManagerDict sang Dict thường
    data = dict(state.info_dict)
    
    # Nếu chưa có dữ liệu
    if not data:
        return JSONResponse({"status": "Waiting for data..."})

    # Logic cũ: enrich dữ liệu (nếu cần)
    try:
        enriched = enrich_info_with_thresholds(data, road_name)
    except:
        enriched = data

    return JSONResponse(enriched)


@router.get("/frames/{road_name}")
async def get_frame_road(road_name: str):
    """
    Lấy frame ảnh hiện tại (Snapshot).
    Đọc từ state.frame_dict
    """
    if state.frame_dict is None or "frame_bytes" not in state.frame_dict:
        return JSONResponse({"error": "Chưa có dữ liệu hình ảnh"}, status_code=404)

    # Lấy bytes ảnh từ bộ nhớ
    frame_bytes = state.frame_dict["frame_bytes"]
    
    return Response(content=frame_bytes, media_type="image/jpeg")


# ========================== WEBSOCKETS (STREAMING) ==========================

@router.websocket("/ws/frames/{road_name}")
async def ws_frames(websocket: WebSocket, road_name: str):
    """
    Stream video qua WebSocket
    """
    await websocket.accept()
    try:
        while True:
            if state.frame_dict and "frame_bytes" in state.frame_dict:
                frame_bytes = state.frame_dict["frame_bytes"]
                # Gửi bytes trực tiếp
                await websocket.send_bytes(frame_bytes)
            
            # Giới hạn FPS gửi đi (ví dụ 30 FPS) để tránh nghẽn mạng
            await asyncio.sleep(0.033) 
            
    except WebSocketDisconnect:
        print("Client ngắt kết nối stream video")
    except Exception as e:
        print(f"Lỗi WebSocket Video: {e}")


@router.websocket("/ws/info/{road_name}")
async def ws_info(websocket: WebSocket, road_name: str):
    """
    Stream thông số xe qua WebSocket
    """
    await websocket.accept()
    try:
        last_data = None
        while True:
            if state.info_dict:
                current_data = dict(state.info_dict)
                
                # Chỉ gửi khi dữ liệu thay đổi để tiết kiệm băng thông (Optional)
                if current_data != last_data:
                    try:
                        enriched = enrich_info_with_thresholds(current_data, road_name)
                    except:
                        enriched = current_data
                    
                    await websocket.send_json(enriched)
                    last_data = current_data
            
            # Cập nhật mỗi 0.5 giây
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print("Client ngắt kết nối stream info")