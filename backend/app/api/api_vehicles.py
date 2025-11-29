from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import asyncio
import time
from multiprocessing import Manager, Process, Queue
from datetime import datetime, timedelta
from sqlalchemy import desc
from datetime import datetime

# Import Config & Service
from app.core.config import settings_metric_transport
from app.services.road_services.AnalyzeOnRoad import run_analyzer 
from app.api import state

# Import Database Modules
from app.db.base import SessionLocal  
# 🔴 FIX 1: Đảm bảo import đúng tên file model (traffic_log số ít)
from app.models.traffic_logs import TrafficLog 

router = APIRouter()

# --- GLOBAL STATE MANAGER ---
class SystemState:
    def __init__(self):
        self.manager = None
        self.info_dict = None   
        self.frame_dict = None  
        self.processes = []     
        self.result_queue = None

# Khởi tạo state toàn cục
sys_state = SystemState()

# ========================== BACKGROUND WORKER (LƯU DB) ==========================
async def save_stats_to_db_worker():
    """
    Worker chạy ngầm: Cứ 10 giây chép dữ liệu từ RAM vào Database
    """
    print("💾 Background Worker: Đã kích hoạt chế độ ghi log giao thông...")
    while True:
        try:
            # Chu kỳ lưu: 10 giây/lần
            await asyncio.sleep(10)
            
            # Chỉ lưu nếu có dữ liệu
            if sys_state.info_dict:
                db = SessionLocal()
                try:
                    for key, data in sys_state.info_dict.items():
                        # key dạng "camera_0" -> lấy id = 0
                        try:
                            cam_id = int(key.split("_")[1])
                        except:
                            continue

                        details = data.get('details', {})
                        
                        log = TrafficLog(
                            camera_id=cam_id,
                            total_vehicles=data.get('total_entered', 0),
                            fps=data.get('fps', 0),
                            # Mapping chi tiết
                            count_car=details.get('car', {}).get('entered', 0),
                            # Gộp xe máy và xe mô tô phân khối lớn (nếu có)
                            count_motor=details.get('motorcycle', {}).get('entered', 0) + details.get('motorbike', {}).get('entered', 0),
                            count_bus=details.get('bus', {}).get('entered', 0),
                            count_truck=details.get('truck', {}).get('entered', 0),
                        )
                        db.add(log)
                    
                    db.commit()
                except Exception as e:
                    print(f"❌ Lỗi worker lưu DB: {e}")
                finally:
                    db.close()
                    
        except Exception as e:
            print(f"❌ Lỗi vòng lặp Worker: {e}")
            await asyncio.sleep(5) 

# ========================== LIFECYCLE EVENTS ==========================

@router.on_event("startup")
async def startup_event():
    # 🔴 FIX 2: QUAN TRỌNG NHẤT - CHỐNG KHỞI ĐỘNG KÉP
    # Nếu manager đã có rồi thì return ngay, không chạy lại code bên dưới
    if sys_state.manager is not None:
        print("⚠️ Hệ thống Traffic AI ĐÃ ĐANG CHẠY. Bỏ qua lệnh khởi động thừa.")
        return
    # -----------------------------------------------------------

    print("🚀 Đang khởi động hệ thống Traffic AI (Multiprocessing)...")
    try:
        # 1. Setup Shared Memory
        sys_state.manager = Manager()
        sys_state.info_dict = sys_state.manager.dict()
        sys_state.frame_dict = sys_state.manager.dict()
        sys_state.result_queue = Queue()

        # 2. Khởi chạy AI Processes
        # ÉP CỨNG SỐ LƯỢNG CAMERA LÀ 2 (Theo tối ưu)
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
            # Nghỉ 1 giây giữa các lần bật cam để tránh sock CPU
            time.sleep(1)
            
        # 3. Kích hoạt Worker lưu DB
        asyncio.create_task(save_stats_to_db_worker())

    except Exception as e:
        print(f"❌ Lỗi khởi động: {e}")

@router.on_event("shutdown")
async def shutdown_event():
    print("🛑 Đang tắt hệ thống Traffic AI...")
    for p in sys_state.processes:
        if p.is_alive():
            p.terminate()
            p.join()
    print("✅ Đã tắt toàn bộ processes.")


# ========================== API ENDPOINTS (DATA & ANALYTICS) ==========================

@router.get("/info/{camera_id}")
async def get_info_road(camera_id: int):
    """Lấy thông tin realtime từ RAM"""
    if sys_state.info_dict is None:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    key = f"camera_{camera_id}"
    if key in sys_state.info_dict:
        return JSONResponse(dict(sys_state.info_dict[key]))
    else:
        return JSONResponse({"status": "waiting", "message": f"No data for Camera {camera_id}"})


@router.get("/frames/{camera_id}")
async def get_frame_road(camera_id: int):
    """Lấy ảnh Snapshot"""
    if sys_state.frame_dict and f"camera_{camera_id}" in sys_state.frame_dict:
        frame_bytes = sys_state.frame_dict[f"camera_{camera_id}"]
        return Response(content=frame_bytes, media_type="image/jpeg")
    return JSONResponse({"error": "No frame"}, status_code=404)


@router.get("/analytics/trend")
async def get_traffic_trend(camera_id: int = 0, minutes: int = 60):
    """
    API: Lấy dữ liệu lịch sử từ Database để vẽ biểu đồ
    """
    db = SessionLocal()
    try:
        time_threshold = datetime.now() - timedelta(minutes=minutes)
        
        logs = db.query(TrafficLog)\
            .filter(TrafficLog.camera_id == camera_id)\
            .filter(TrafficLog.timestamp >= time_threshold)\
            .order_by(TrafficLog.timestamp.asc())\
            .all()
            
        result = []
        for log in logs:
            result.append({
                "time": log.timestamp.strftime("%H:%M"),
                "count": log.total_vehicles,
                "car": log.count_car,
                "motor": log.count_motor
            })
            
        return JSONResponse(result)
    except Exception as e:
        print(f"Lỗi Analytics API: {e}")
        return JSONResponse([])
    finally:
        db.close()


# ========================== WEBSOCKETS (STREAMING) ==========================

@router.websocket("/ws/frames/{camera_id}")
async def ws_frames(websocket: WebSocket, camera_id: int):
    """Stream Video (Chỉ gửi khi ảnh thay đổi)"""
    await websocket.accept()
    key = f"camera_{camera_id}"
    last_frame_data = None
    
    try:
        while True:
            if sys_state.frame_dict and key in sys_state.frame_dict:
                current_frame_data = sys_state.frame_dict[key]
                if current_frame_data != last_frame_data:
                    await websocket.send_bytes(current_frame_data)
                    last_frame_data = current_frame_data
            await asyncio.sleep(0.05) 
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/ws/info/{camera_id}")
async def ws_info(websocket: WebSocket, camera_id: int):
    """Stream Info (Realtime từ RAM)"""
    await websocket.accept()
    key = f"camera_{camera_id}"
    last_ts = 0
    
    try:
        while True:
            if sys_state.info_dict and key in sys_state.info_dict:
                current_data = dict(sys_state.info_dict[key])
                current_ts = current_data.get('timestamp', 0)
                if current_ts != last_ts:
                    await websocket.send_json(current_data)
                    last_ts = current_ts
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
