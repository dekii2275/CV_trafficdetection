from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import asyncio
import time
from multiprocessing import Manager, Process, Queue
from datetime import datetime, timedelta
from sqlalchemy import desc, func, cast, Date
import pandas as pd

# Import Config & Service
from app.core.config import settings_metric_transport
from app.services.road_services.AnalyzeOnRoad import run_analyzer 
from app.api import state

# Import Database Modules
from app.db.base import SessionLocal  
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

sys_state = SystemState()

# ========================== BACKGROUND WORKER ==========================
async def save_stats_to_db_worker():
    print("💾 Background Worker: Đã kích hoạt chế độ ghi log giao thông...")
    while True:
        try:
            await asyncio.sleep(10)
            if sys_state.info_dict:
                db = SessionLocal()
                try:
                    current_snapshot = dict(sys_state.info_dict)
                    for key, data in current_snapshot.items():
                        try:
                            if "_" not in key: continue 
                            cam_id = int(key.split("_")[1])
                        except: continue

                        details = data.get('details', {})
                        log = TrafficLog(
                            camera_id=cam_id,
                            total_vehicles=data.get('total_entered', 0),
                            fps=data.get('fps', 0),
                            count_car=details.get('car', {}).get('entered', 0),
                            count_motor=(
                                details.get('motorcycle', {}).get('entered', 0) + 
                                details.get('motorbike', {}).get('entered', 0) + 
                                details.get('motor', {}).get('entered', 0)
                            ),
                            count_bus=details.get('bus', {}).get('entered', 0),
                            count_truck=details.get('truck', {}).get('entered', 0),
                            timestamp=datetime.now()
                        )
                        db.add(log)
                    db.commit()
                except Exception as e:
                    print(f"❌ Lỗi worker lưu DB: {e}")
                    db.rollback() 
                finally:
                    db.close()
        except Exception as e:
            print(f"❌ Lỗi vòng lặp Worker: {e}")
            await asyncio.sleep(5) 

# ========================== LIFECYCLE ==========================
@router.on_event("startup")
async def startup_event():
    if sys_state.manager is not None:
        print("⚠️ Hệ thống Traffic AI ĐÃ ĐANG CHẠY.")
        return

    print("🚀 Đang khởi động hệ thống Traffic AI (Multiprocessing)...")
    try:
        sys_state.manager = Manager()
        sys_state.info_dict = sys_state.manager.dict()
        sys_state.frame_dict = sys_state.manager.dict()
        sys_state.result_queue = Queue()

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


# ========================== API ENDPOINTS ==========================

@router.get("/info/{camera_id}")
async def get_info_road(camera_id: int):
    """Lấy thông tin realtime từ RAM"""
    if sys_state.info_dict is None:
        return JSONResponse({"error": "System not initialized"}, status_code=500)
    key = f"camera_{camera_id}"
    data = sys_state.info_dict.get(key)
    if data: return JSONResponse(dict(data))
    return JSONResponse({"status": "waiting"}, status_code=404)

# 🔥 FIX LỖI 404: Thêm lại API /stats nhưng dùng dữ liệu RAM
@router.get("/stats/{camera_id}")
async def get_stats_legacy(camera_id: int):
    if sys_state.info_dict is None: return JSONResponse({}, status_code=404)
    key = f"camera_{camera_id}"
    data = sys_state.info_dict.get(key)
    if data: return JSONResponse(dict(data))
    return JSONResponse({"status": "waiting"}, status_code=404)

@router.get("/frames/{camera_id}")
async def get_frame_road(camera_id: int):
    """Lấy ảnh Snapshot"""
    key = f"camera_{camera_id}"
    if sys_state.frame_dict and key in sys_state.frame_dict:
        frame_bytes = sys_state.frame_dict[key]
        return Response(content=frame_bytes, media_type="image/jpeg")
    return JSONResponse({"error": "No frame"}, status_code=404)

# ========================== ANALYTICS (DATABASE) ==========================

# 🔥 FIX LỖI 404: Đổi tên /analytics/advanced thành /analyze
@router.get("/analyze/{camera_id}")
async def get_advanced_stats(camera_id: int):
    """Phân tích nâng cao (Pandas + DB)"""
    db = SessionLocal()
    try:
        time_threshold = datetime.now() - timedelta(minutes=60)
        query = db.query(
            TrafficLog.timestamp, TrafficLog.total_vehicles,
            TrafficLog.count_car, TrafficLog.count_motor,
            TrafficLog.count_truck, TrafficLog.count_bus
        ).filter(
            TrafficLog.camera_id == camera_id,
            TrafficLog.timestamp >= time_threshold
        ).statement
        
        df = pd.read_sql(query, db.bind)
        
        if df.empty:
            return JSONResponse({"message": "Chưa đủ dữ liệu"})

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df_1min = df.resample('1min').mean().fillna(0)
        
        if len(df_1min) < 2: return JSONResponse({"message": "Đang thu thập..."})

        current_val = df_1min['total_vehicles'].iloc[-1]
        mean_val = df_1min['total_vehicles'].mean()
        std_val = df_1min['total_vehicles'].std()
        
        # Trend detection
        recent_avg = df_1min['total_vehicles'].tail(5).mean()
        prev_avg = df_1min['total_vehicles'].iloc[-10:-5].mean() if len(df_1min) > 10 else mean_val
        trend_pct = ((recent_avg - prev_avg) / prev_avg * 100) if prev_avg > 0 else 0

        stats = {
            "current_flow": int(current_val),
            "average_flow": round(float(mean_val), 1),
            "peak_flow": int(df_1min['total_vehicles'].max()),
            "volatility": f"{round(std_val, 1)}",
            "status": "Cao điểm" if current_val > (mean_val + std_val) else "Bình thường",
            "trend_percent": round(trend_pct, 1),
            "composition": {
                "car": int(df['count_car'].sum()),
                "motor": int(df['count_motor'].sum()),
                "truck": int(df['count_truck'].sum()),
                "bus": int(df['count_bus'].sum())
            }
        }
        return JSONResponse(stats)
    except Exception as e:
        print(f"Lỗi Analyze: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        db.close()

@router.get("/charts/vehicle-distribution")
async def get_vehicle_distribution():
    """Pie Chart Data"""
    db = SessionLocal()
    try:
        today = datetime.now().date()
        subquery = db.query(func.max(TrafficLog.id))\
            .filter(cast(TrafficLog.timestamp, Date) == today)\
            .group_by(TrafficLog.camera_id)
        latest_logs = db.query(TrafficLog).filter(TrafficLog.id.in_(subquery)).all()
        
        total_car = sum(log.count_car for log in latest_logs)
        total_motor = sum(log.count_motor for log in latest_logs)
        total_bus = sum(log.count_bus for log in latest_logs)
        total_truck = sum(log.count_truck for log in latest_logs)
        total_all = sum(log.total_vehicles for log in latest_logs)
        
        def _pct(val, total): return float(val)/total if total > 0 else 0.0

        return JSONResponse({
            "date": today.isoformat(),
            "totals": {
                "car": total_car, "motor": total_motor,
                "bus": total_bus, "truck": total_truck,
                "total_vehicles": total_all
            },
            "percentages": {
                "car": _pct(total_car, total_all),
                "motor": _pct(total_motor, total_all),
                "bus": _pct(total_bus, total_all),
                "truck": _pct(total_truck, total_all)
            }
        })
    finally:
        db.close()
@router.get("/charts/time-series/{camera_id}")
async def get_time_series_data(camera_id: int, hours: int = 12):
    """Trả về dữ liệu time series để vẽ line chart (từ database)"""
    db = SessionLocal()
    try:
        time_threshold = datetime.now() - timedelta(hours=hours)
        query = db.query(
            TrafficLog.timestamp,
            TrafficLog.total_vehicles
        ).filter(
            TrafficLog.camera_id == camera_id,
            TrafficLog.timestamp >= time_threshold
        ).order_by(TrafficLog.timestamp).statement
        
        df = pd.read_sql(query, db.bind)
        
        if df.empty:
            return JSONResponse({"message": "Chưa đủ dữ liệu"})
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample theo giờ (hoặc phút tùy yêu cầu)
        df_hourly = df.resample('1h').sum().fillna(0)
        
        # Format dữ liệu cho frontend
        data_points = []
        for idx, row in df_hourly.iterrows():
            hour_label = idx.strftime('%H:00')
            data_points.append({
                "label": hour_label,
                "value": int(row['total_vehicles'])
            })
        
        return JSONResponse({
            "camera_id": camera_id,
            "points": data_points,
            "period_hours": hours
        })
    except Exception as e:
        print(f"Lỗi Time Series: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        db.close()
    
# ========================== WEBSOCKETS ==========================

@router.websocket("/ws/frames/{camera_id}")
async def ws_frames(websocket: WebSocket, camera_id: int):
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
    except Exception: pass

@router.websocket("/ws/info/{camera_id}")
async def ws_info(websocket: WebSocket, camera_id: int):
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
    except Exception: pass