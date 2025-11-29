from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import asyncio
import time
from multiprocessing import Manager, Process, Queue
from datetime import datetime, timedelta
from sqlalchemy import desc

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