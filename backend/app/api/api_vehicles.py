from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import asyncio
import cv2
import numpy as np
from multiprocessing import Manager, Process, Queue
import time
import sys
import multiprocessing
from pathlib import Path   # thêm
import json                # thêm
import os 
from datetime import datetime

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

@router.get("/stats/{camera_id}")
async def get_camera_stats(camera_id: int):
    """
    Đọc file JSON thống kê trong logs/traffic_count
    Định dạng file mới: cam{camera_id}_YYYYMMDD.json (hoặc YYMMDD – phải khớp với chỗ lưu)
    """
    try:
        log_dir = Path("logs/traffic_count")
        if not log_dir.exists():
            return JSONResponse(
                {"error": "Log directory not found", "detail": str(log_dir)},
                status_code=404
            )

        # Ngày hôm nay
        today = datetime.now()

        # !!! QUAN TRỌNG:
        # Nếu lúc lưu bạn dùng %Y%m%d (20251129) thì để đúng như dòng dưới;
        # nếu bạn dùng %y%m%d (251129) thì sửa lại cho trùng.
        date_str = today.strftime("%Y%m%d")   # hoặc "%y%m%d" nếu bạn đang dùng 2 số năm

        # Tên file phải khớp với AnalyzeOnRoadBase
        file_path = log_dir / f"cam{camera_id}_{date_str}.json"

        if not file_path.exists():
            return JSONResponse(
                {
                    "error": "No log file found for this camera today",
                    "camera_id": camera_id,
                    "date": today.date().isoformat()
                },
                status_code=404
            )

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return JSONResponse(data)

    except Exception as e:
        print(f"[get_camera_stats] Error reading JSON for camera {camera_id}: {e}")
        return JSONResponse(
            {"error": "Internal server error while reading stats JSON"},
            status_code=500
        )


@router.get("/dashboard/{camera_id}")
async def get_camera_dashboard(camera_id: int):
    """
    API phục vụ dashboard:
    - Đọc file JSON theo NGÀY: cam{camera_id}_YYYYMMDD.json
    - current_stats: car, motor, truck, bus, total_vehicles của khung giờ hiện tại (now.hour)
    - daily_total: tổng tất cả total_vehicles trong ngày (sum 24 dict)
    """
    try:
        log_dir = Path("logs/traffic_count")
        if not log_dir.exists():
            return JSONResponse(
                {"error": "Log directory not found", "detail": str(log_dir)},
                status_code=404
            )

        # Ngày hôm nay
        now = datetime.now()
        today = now.date()
        date_str_file = today.strftime("%Y%m%d")   # dùng trong tên file
        date_str_display = today.isoformat()       # dùng để hiển thị

        # Tên file phải khớp với logic lưu trong AnalyzeOnRoadBase:
        # cam{video_index}_{YYYYMMDD}.json
        file_path = log_dir / f"cam{camera_id}_{date_str_file}.json"

        if not file_path.exists():
            return JSONResponse(
                {
                    "error": "No log file for today",
                    "camera_id": camera_id,
                    "date": date_str_display
                },
                status_code=404
            )

        # Đọc dữ liệu trong file
        with file_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Hỗ trợ 2 dạng:
        # - list 24 dict (định dạng mới)
        # - dict đơn (định dạng cũ) -> wrap vào list cho khỏi lỗi
        if isinstance(raw_data, list):
            hourly_data = raw_data
        elif isinstance(raw_data, dict):
            hourly_data = [raw_data]
        else:
            return JSONResponse(
                {
                    "error": "Invalid JSON format",
                    "detail": "Expected list[dict] or dict"
                },
                status_code=500
            )

        if len(hourly_data) == 0:
            return JSONResponse(
                {
                    "error": "Empty stats file",
                    "camera_id": camera_id,
                    "date": date_str_display
                },
                status_code=500
            )

        # Khung giờ hiện tại (0..23), tránh index out of range nếu list nhỏ hơn 24
        hour_index = min(now.hour, len(hourly_data) - 1)
        current_hour_data = hourly_data[hour_index] or {}

        # Thông số tại thời điểm hiện tại
        current_stats = {
            "car": int(current_hour_data.get("car", 0) or 0),
            "motor": int(current_hour_data.get("motor", 0) or 0),
            "bus": int(current_hour_data.get("bus", 0) or 0),
            "truck": int(current_hour_data.get("truck", 0) or 0),
            "total_vehicles": int(current_hour_data.get("total_vehicles", 0) or 0),
        }

        # Tổng lượt xe trong ngày = sum total_vehicles của tất cả dict trong list
        daily_total = 0
        for item in hourly_data:
            if isinstance(item, dict):
                daily_total += int(item.get("total_vehicles", 0) or 0)

        # Response chuẩn cho frontend dashboard
        resp = {
            "camera_id": camera_id,
            "date": date_str_display,
            "current_hour": hour_index,
            "current_stats": current_stats,
            "daily_total": daily_total,
        }

        return JSONResponse(resp)

    except Exception as e:
        print(f"[get_camera_dashboard] Error for camera {camera_id}: {e}")
        return JSONResponse(
            {"error": "Internal server error while reading dashboard stats"},
            status_code=500
        )

# ===================== HELPER ĐỌC LOG THEO NGÀY =====================

def _load_camera_daily_data(camera_id: int, target_date=None):
    """
    Đọc file log theo ngày của 1 camera.
    Trả về list[dict] (mỗi dict là 1 giờ) hoặc None nếu không có file / lỗi.
    """
    try:
        log_dir = Path("logs/traffic_count")
        if not log_dir.exists():
            return None

        if target_date is None:
            target_date = datetime.now().date()

        date_str = target_date.strftime("%Y%m%d")
        file_path = log_dir / f"cam{camera_id}_{date_str}.json"

        if not file_path.exists():
            return None

        with file_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, list):
            return raw
        elif isinstance(raw, dict):
            # format cũ: 1 dict → wrap vào list cho dễ xử lý
            return [raw]
        else:
            return None
    except Exception as e:
        print(f"[_load_camera_daily_data] Error loading camera {camera_id}: {e}")
        return None

@router.get("/charts/vehicle-distribution")
async def get_vehicle_distribution():
    """
    Tổng hợp phân bố theo loại phương tiện trong NGÀY HÔM NAY,
    gộp tất cả các camera đang chạy.
    """
    today = datetime.now().date()

    # Lấy số camera đang chạy từ sys_state.processes (đã khởi tạo ở startup)
    num_cameras_config = len(sys_state.processes) if sys_state.processes else 0

    if num_cameras_config == 0:
        return JSONResponse(
            {"error": "No active cameras in system"},
            status_code=500,
        )

    total_car = 0
    total_truck = 0
    total_bike = 0    # motor
    total_bus = 0
    used_cameras = 0

    # Duyệt qua tất cả camera đang chạy
    for cam_id in range(num_cameras_config):
        day_data = _load_camera_daily_data(cam_id, today)
        if not day_data:
            continue

        used_cameras += 1

        for item in day_data:
            if not isinstance(item, dict):
                continue
            total_car += int(item.get("car", 0) or 0)
            total_truck += int(item.get("truck", 0) or 0)
            total_bike += int(item.get("motor", 0) or 0)
            total_bus += int(item.get("bus", 0) or 0)

    if used_cameras == 0:
        return JSONResponse(
            {
                "error": "No log files for today",
                "date": today.isoformat(),
            },
            status_code=404,
        )

    total_all = total_car + total_truck + total_bike + total_bus

    def _pct(x: int, base: int) -> float:
        return float(x) / base if base > 0 else 0.0

    resp = {
        "date": today.isoformat(),
        "num_cameras": used_cameras,
        "totals": {
            "car": total_car,
            "truck": total_truck,
            "bike": total_bike,
            "bus": total_bus,
            "total_vehicles": total_all,
        },
        "percentages": {
            "car": _pct(total_car, total_all),
            "truck": _pct(total_truck, total_all),
            "bike": _pct(total_bike, total_all),
            "bus": _pct(total_bus, total_all),
        },
    }
    return JSONResponse(resp)

@router.get("/charts/hourly-flow")
async def get_hourly_flow():
    """
    Lưu lượng theo giờ trong NGÀY HÔM NAY,
    gộp tất cả camera (tổng số total_vehicles mỗi giờ).
    """
    today = datetime.now().date()
    now = datetime.now()
    current_hour = now.hour

    num_cameras_config = len(sys_state.processes) if sys_state.processes else 0
    if num_cameras_config == 0:
        return JSONResponse(
            {"error": "No active cameras in system"},
            status_code=500,
        )

    # Khởi tạo 24 giờ = 0
    hours = [
        {"hour": h, "label": f"{h:02d}h", "total_vehicles": 0}
        for h in range(24)
    ]

    used_cameras = 0

    for cam_id in range(num_cameras_config):
        day_data = _load_camera_daily_data(cam_id, today)
        if not day_data:
            continue

        used_cameras += 1

        max_h = min(24, len(day_data))
        for h in range(max_h):
            item = day_data[h]
            if not isinstance(item, dict):
                continue
            hours[h]["total_vehicles"] += int(item.get("total_vehicles", 0) or 0)

    if used_cameras == 0:
        return JSONResponse(
            {
                "error": "No log files for today",
                "date": today.isoformat(),
            },
            status_code=404,
        )

    # Cắt tới giờ hiện tại để tránh đuôi toàn 0
    hours_trimmed = [entry for entry in hours if entry["hour"] <= current_hour]

    resp = {
        "date": today.isoformat(),
        "num_cameras": used_cameras,
        "hours": hours_trimmed,
    }
    return JSONResponse(resp)
