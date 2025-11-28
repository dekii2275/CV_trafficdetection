from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import asyncio
import cv2
import numpy as np
from multiprocessing import Manager, Process, Queue
import time
import sys

# Import config
from app.core.config import settings_metric_transport

# CHÚ Ý: Import hàm run_analyzer (không phải class)
from app.services.road_services.AnalyzeOnRoad import run_analyzer 

# Import state global (chỉ để dùng biến, không import class từ đó)
from app.api import state

router = APIRouter()

# --- GLOBAL STATE MANAGER ---
class SystemState:
    def __init__(self):
        self.manager = None
        self.info_dict = None   # Chứa thông tin đếm xe: {'camera_0': {...}}
        self.frame_dict = None  # Chứa bytes hình ảnh: {'camera_0': b'\xff...'}
        self.processes = []     # Danh sách các tiến trình đang chạy
        self.result_queue = None

# Khởi tạo state toàn cục
sys_state = SystemState()

# ========================== LIFECYCLE EVENTS ==========================

@router.on_event("startup")
async def startup_event():
    print("🚀 Đang khởi động hệ thống Traffic AI (Multiprocessing)...")
    try:
        sys_state.manager = Manager()
        sys_state.info_dict = sys_state.manager.dict()
        sys_state.frame_dict = sys_state.manager.dict()
        sys_state.result_queue = Queue()

        # ÉP CỨNG SỐ LƯỢNG CAMERA LÀ 2 (Để giảm tải CPU)
        # Thay vì lấy hết trong config
        num_cameras = 2 

        print(f"📹 Kích hoạt {num_cameras} cameras tối ưu...")

        for i in range(num_cameras):
            p = Process(
                target=run_analyzer,
                args=(i, sys_state.info_dict, sys_state.result_queue, sys_state.frame_dict, False)
            )
            p.start()
            sys_state.processes.append(p)
            print(f"✅ Camera {i} started (PID: {p.pid})")
            time.sleep(1) 

    except Exception as e:
        print(f"❌ Lỗi khởi động: {e}")

@router.on_event("shutdown")
async def shutdown_event():
    """
    Dọn dẹp processes khi tắt API
    """
    print("🛑 Đang tắt hệ thống Traffic AI...")
    for p in sys_state.processes:
        if p.is_alive():
            p.terminate()
            p.join()
    print("✅ Đã tắt toàn bộ processes.")


# ========================== API ENDPOINTS ==========================

@router.get("/info/{camera_id}")
async def get_info_road(camera_id: int):
    """
    Lấy thông tin đếm xe từ bộ nhớ chia sẻ.
    """
    if sys_state.info_dict is None:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    key = f"camera_{camera_id}"
    
    # Lấy dữ liệu từ Manager Dict (cần copy ra dict thường để return JSON)
    if key in sys_state.info_dict:
        data = dict(sys_state.info_dict[key])
        return JSONResponse(data)
    else:
        return JSONResponse({"status": "waiting", "message": f"No data for Camera {camera_id} yet"})


@router.get("/frames/{camera_id}")
async def get_frame_road(camera_id: int):
    """
    Lấy ảnh Snapshot (JPEG) hiện tại của camera
    """
    if sys_state.frame_dict is None:
        return Response(status_code=500)

    key = f"camera_{camera_id}"
    
    if key in sys_state.frame_dict:
        frame_bytes = sys_state.frame_dict[key]
        return Response(content=frame_bytes, media_type="image/jpeg")
    else:
        return JSONResponse({"error": "No frame data"}, status_code=404)


# ========================== WEBSOCKETS (STREAMING) ==========================

# =======================================================
# 2. SỬA HÀM WEBSOCKET: Chỉ gửi khi frame thay đổi
# =======================================================
@router.websocket("/ws/frames/{camera_id}")
async def ws_frames(websocket: WebSocket, camera_id: int):
    await websocket.accept()
    key = f"camera_{camera_id}"
    last_frame_data = None # Biến nhớ frame cũ
    
    try:
        while True:
            if sys_state.frame_dict and key in sys_state.frame_dict:
                current_frame_data = sys_state.frame_dict[key]
                
                # CHỈ GỬI NẾU KHÁC CŨ
                if current_frame_data != last_frame_data:
                    await websocket.send_bytes(current_frame_data)
                    last_frame_data = current_frame_data
            
            # Ngủ 0.05s (~20 FPS) là đủ mượt cho mắt người
            await asyncio.sleep(0.05) 
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Error: {e}")


@router.websocket("/ws/info/{camera_id}")
async def ws_info(websocket: WebSocket, camera_id: int):
    """
    Stream thông số đếm xe realtime
    """
    await websocket.accept()
    key = f"camera_{camera_id}"
    last_ts = 0
    
    try:
        while True:
            if sys_state.info_dict and key in sys_state.info_dict:
                current_data = dict(sys_state.info_dict[key])
                current_ts = current_data.get('timestamp', 0)
                
                # Chỉ gửi khi có dữ liệu mới (dựa vào timestamp)
                if current_ts != last_ts:
                    await websocket.send_json(current_data)
                    last_ts = current_ts
            
            # Cập nhật mỗi 0.5 giây
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print(f"Client disconnected info Camera {camera_id}")