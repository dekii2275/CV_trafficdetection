from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse, Response
import asyncio
import time
from multiprocessing import Manager, Process, Queue
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import desc, func, cast, Date
import pandas as pd

# Import Config & Service
from app.core.config import settings_metric_transport
from app.services.road_services.AnalyzeOnRoad import run_analyzer 
from app.api import state

# Import Database Modules
from app.db.base import SessionLocal  
from app.models.traffic_logs import TrafficLog 

from sqlalchemy.orm import Session
import numpy as np

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

LOCAL_TZ = ZoneInfo("Asia/Bangkok")
VEHICLE_CLASSES = ["count_car", "count_motor", "count_bus", "count_truck"]



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def load_traffic_df(
    db: Session,
    camera_id: int,
    hours: int = 24,
    freq: str = "1min",
):
    """
    Query TrafficLog từ DB, chuẩn hóa về UTC+7, resample theo freq.
    Trả về (df_resampled, classes_thực_tế)
    """
    now_utc = datetime.now(timezone.utc)
    threshold_utc = now_utc - timedelta(hours=hours)

    query = (
        db.query(TrafficLog)
        .filter(
            TrafficLog.camera_id == camera_id,
            TrafficLog.timestamp >= threshold_utc,
        )
        .order_by(TrafficLog.timestamp.asc())
    )

    df = pd.read_sql(query.statement, db.bind)

    if df.empty:
        return df, []

    # timestamp -> UTC -> local (UTC+7)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp_local"] = df["timestamp"].dt.tz_convert(LOCAL_TZ)
    df = df.set_index("timestamp_local")

    # Chỉ lấy những cột class đang tồn tại
    classes = [c for c in VEHICLE_CLASSES if c in df.columns]

    # Chuẩn hóa cột total
    if "total_vehicles" in df.columns:
        df["total"] = df["total_vehicles"]
    elif "total" not in df.columns and classes:
        df["total"] = df[classes].sum(axis=1)

    # Resample
    df_resampled = df.resample(freq).max().ffill()
    df_resampled.index.name = "time"

    return df_resampled, classes





# BACKGROUND WORKER
async def save_stats_to_db_worker():
    print("Background Worker: Đã kích hoạt chế độ ghi log giao thông...")
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
                    print(f"Lỗi worker lưu DB: {e}")
                    db.rollback() 
                finally:
                    db.close()
        except Exception as e:
            print(f"Lỗi vòng lặp Worker: {e}")
            await asyncio.sleep(5) 

# ========================== LIFECYCLE ==========================
@router.on_event("startup")
async def startup_event():
    if sys_state.manager is not None:
        print("Hệ thống Traffic AI ĐÃ ĐANG CHẠY.")
        return

    print("Đang khởi động hệ thống Traffic AI (Multiprocessing)...")
    try:
        sys_state.manager = Manager()
        sys_state.info_dict = sys_state.manager.dict()
        sys_state.frame_dict = sys_state.manager.dict()
        sys_state.result_queue = Queue()

        num_cameras = 2 
        print(f"Kích hoạt {num_cameras} cameras tối ưu...")

        for i in range(num_cameras):
            p = Process(
                target=run_analyzer,
                args=(i, sys_state.info_dict, sys_state.result_queue, sys_state.frame_dict, False)
            )
            p.start()
            sys_state.processes.append(p)
            print(f"Camera {i} started (PID: {p.pid})")
            time.sleep(1)
            
        asyncio.create_task(save_stats_to_db_worker())

    except Exception as e:
        print(f"Lỗi khởi động: {e}")

@router.on_event("shutdown")
async def shutdown_event():
    print("Đang tắt hệ thống Traffic AI...")
    for p in sys_state.processes:
        if p.is_alive():
            p.terminate()
            p.join()
    print("Đã tắt toàn bộ processes.")


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


@router.get("/frames/{camera_id}")
async def get_frame_road(camera_id: int):
    """Lấy ảnh Snapshot"""
    key = f"camera_{camera_id}"
    if sys_state.frame_dict and key in sys_state.frame_dict:
        frame_bytes = sys_state.frame_dict[key]
        return Response(content=frame_bytes, media_type="image/jpeg")
    return JSONResponse({"error": "No frame"}, status_code=404)


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
async def get_time_series_data(camera_id: int, minutes: int = 60):
    """
    Lấy time-series cho camera, chuyển timestamp về Asia/Bangkok (UTC+7)
    -> GIÁ TRỊ THEO TỪNG PHÚT (không cộng dồn)
    """
    db: Session = SessionLocal()
    try:
        tz_local = ZoneInfo("Asia/Bangkok")

        # Lấy thời gian hiện tại theo UTC
        now_utc = datetime.now(timezone.utc)
        # Lấy rộng 24h cho an toàn (đủ dữ liệu để resample + diff)
        time_threshold_utc = now_utc - timedelta(hours=24)

        print(f"[DEBUG] Current Time UTC: {now_utc}")
        print(f"[DEBUG] Threshold UTC:    {time_threshold_utc}")

        query = (
            db.query(TrafficLog)
            .filter(
                TrafficLog.camera_id == camera_id,
                TrafficLog.timestamp >= time_threshold_utc,
            )
            .order_by(TrafficLog.timestamp.asc())
        )

        df = pd.read_sql(query.statement, db.bind)
        print(f"[DEBUG] Found {len(df)} records in last 24h (UTC).")
        if df.empty:
            return JSONResponse(
                {
                    "camera_id": camera_id,
                    "points": [],
                    "message": "DB Empty in last 24h",
                }
            )

        # --- CHUYỂN MÚI GIỜ ---
        # Giả sử DB lưu UTC
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["timestamp"] = df["timestamp"].dt.tz_convert(tz_local)

        print(f"[DEBUG] First record (local): {df['timestamp'].iloc[0]}")
        print(f"[DEBUG] Last  record (local): {df['timestamp'].iloc[-1]}")

        df.set_index("timestamp", inplace=True)

        # Resample theo phút: lấy max (vì total_vehicles là tích lũy), rồi ffill
        df_resampled = df.resample("1min").max().ffill()

        # ===== TÍNH SỐ XE MỖI PHÚT (KHÔNG CỘNG DỒN) =====
        # total_vehicles(t) - total_vehicles(t-1)
        df_resampled["vehicles_per_min"] = (
            df_resampled["total_vehicles"]
            .diff()          # hiệu giữa 2 phút
            .fillna(0)       # phút đầu tiên -> 0
            .clip(lower=0)   # tránh âm nếu counter reset
            .astype(int)
        )

        # Lấy N phút gần nhất (theo tham số minutes)
        # Mỗi dòng = 1 phút → lấy tail(minutes) là được
        tail_df = df_resampled.tail(minutes)

        data_points = []
        for idx, row in tail_df.iterrows():
            val = int(row["vehicles_per_min"])
            data_points.append(
                {
                    "label": idx.strftime("%H:%M"),  # đã là giờ UTC+7
                    "value": val,                    # số xe trong phút đó
                }
            )

        return JSONResponse(
            {
                "camera_id": camera_id,
                "points": data_points,
                "period": f"{minutes}m",
                "timezone": "Asia/Bangkok (UTC+7)",
                "aggregation": "per_minute",  # optional: gửi thêm meta cho frontend
            }
        )

    except Exception as e:
        print(f"ERROR: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        db.close()

@router.get("/charts/grouped-bar/{camera_id}")
async def grouped_bar_chart(
    camera_id: int,
    minutes: int = 60,
    db: Session = Depends(get_db),
):
    
    # Dùng lại helper đọc DB + convert UTC -> UTC+7
    df, classes = load_traffic_df(db, camera_id, hours=24, freq="1min")

    if df.empty or not classes:
        return JSONResponse(
            {
                "camera_id": camera_id,
                "points": [],
                "message": "No data in last 24h",
            }
        )

    # Lấy minutes điểm cuối (giống time-series)
    tail = df.tail(minutes)

    points = []
    for idx, row in tail.iterrows():
        values = {}
        for c in classes:
            v = row.get(c, 0)
            # đảm bảo là int
            values[c] = int(v) if pd.notna(v) else 0

        points.append(
            {
                "label": idx.strftime("%H:%M"),  # đã là giờ UTC+7 trong load_traffic_df
                "values": values,
            }
        )

    return JSONResponse(
        {
            "camera_id": camera_id,
            "points": points,
            "classes": classes,  # để frontend biết thứ tự / legend
            "period": f"{minutes}m",
            "timezone": "Asia/Bangkok (UTC+7)",
        }
    )


@router.get("/charts/area/{camera_id}")
async def area_chart(
    camera_id: int,
    minutes: int = 60,
    db: Session = Depends(get_db),
):
    
    df, classes = load_traffic_df(db, camera_id, hours=24, freq="1min")

    if df.empty or not classes:
        return JSONResponse(
            {
                "camera_id": camera_id,
                "points": [],
                "message": "No data in last 24h",
            }
        )

    tail = df.tail(minutes)

    points = []
    for idx, row in tail.iterrows():
        values = {}
        for c in classes:
            v = row.get(c, 0)
            values[c] = int(v) if pd.notna(v) else 0

        points.append(
            {
                "label": idx.strftime("%H:%M"),  
                "values": values,
            }
        )

    return JSONResponse(
        {
            "camera_id": camera_id,
            "points": points,
            "classes": classes,
            "period": f"{minutes}m",
            "timezone": "Asia/Bangkok (UTC+7)",
            "chart_type": "stacked_area",
        }
    )




@router.get("/charts/hist-total/{camera_id}")
async def hist_total(
    camera_id: int,
    bins: int = 20,
    db: Session = Depends(get_db),
):
   
    df, _ = load_traffic_df(db, camera_id, hours=24, freq="1min")

    if df.empty or "total" not in df.columns:
        return JSONResponse(
            {
                "camera_id": camera_id,
                "points": [],
                "bins": bins,
                "message": "No data or 'total' column missing",
            }
        )

    values = df["total"].dropna().astype(int).to_numpy()
    if len(values) == 0:
        return JSONResponse(
            {
                "camera_id": camera_id,
                "points": [],
                "bins": bins,
                "message": "No total values",
            }
        )

    counts, bin_edges = np.histogram(values, bins=bins)
    bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2.0)

    # Chuẩn hoá về dạng points: [{label, value}]
    points = [
        {
            "label": f"{center:.1f}",      # nhãn là mid-point của bin
            "value": int(count),           # số lượng điểm rơi vào bin
        }
        for center, count in zip(bin_centers, counts)
    ]

    return JSONResponse(
        {
            "camera_id": camera_id,
            "points": points,
            "bins": bins,
            "metric": "total_vehicles",
        }
    )



@router.get("/charts/boxplot/{camera_id}")
async def boxplot_chart(
    camera_id: int,
    db: Session = Depends(get_db),
):
    
    df, classes = load_traffic_df(db, camera_id, hours=24, freq="1min")

    if df.empty or not classes:
        return JSONResponse(
            {
                "camera_id": camera_id,
                "items": [],
                "classes": [],
                "message": "No data in last 24h",
            }
        )

    items = []
    for c in classes:
        s = df[c].dropna().astype(float)
        if s.empty:
            continue
        desc = s.describe()  # count, mean, std, min, 25%, 50%, 75%, max
        items.append(
            {
                "name": c,
                "min": float(desc["min"]),
                "q1": float(desc["25%"]),
                "median": float(desc["50%"]),
                "q3": float(desc["75%"]),
                "max": float(desc["max"]),
            }
        )

    return JSONResponse(
        {
            "camera_id": camera_id,
            "items": items,
            "classes": classes,
        }
    )


@router.get("/charts/rolling-avg/{camera_id}")
async def rolling_avg_chart(
    camera_id: int,
    minutes: int = 60,
    window: int = 5,
    db: Session = Depends(get_db),
):
   
    df, classes = load_traffic_df(db, camera_id, hours=24, freq="1min")

    if df.empty or not classes:
        return JSONResponse(
            {
                "camera_id": camera_id,
                "points": [],
                "classes": [],
                "window": window,
                "message": "No data in last 24h",
            }
        )

    # Tính rolling mean theo window
    df_ra = df[classes].rolling(window=window).mean()
    tail = df_ra.tail(minutes)

    points = []
    for idx, row in tail.iterrows():
        values = {}
        for c in classes:
            v = row.get(c, None)
            values[c] = float(v) if pd.notna(v) else 0.0

        points.append(
            {
                "label": idx.strftime("%H:%M"),  # đã là giờ UTC+7 trong load_traffic_df
                "values": values,
            }
        )

    return JSONResponse(
        {
            "camera_id": camera_id,
            "points": points,
            "classes": classes,
            "window": window,
            "period": f"{minutes}m",
            "timezone": "Asia/Bangkok (UTC+7)",
        }
    )


@router.get("/charts/peaks/{camera_id}")
async def peak_detection_chart(
    camera_id: int,
    minutes: int = 60,
    db: Session = Depends(get_db),
):
    
    df, _ = load_traffic_df(db, camera_id, hours=24, freq="1min")

    if df.empty or "total" not in df.columns:
        return JSONResponse(
            {
                "camera_id": camera_id,
                "points": [],
                "peaks": [],
                "message": "No data or 'total' missing",
            }
        )

    # Nếu DB chưa có cột is_peak_auto, có thể tự tính như sau:
    if "is_peak_auto" not in df.columns:
        # ví dụ: peak = những điểm >= quantile 0.9
        thr = df["total"].quantile(0.9)
        df["is_peak_auto"] = df["total"] >= thr

    tail = df.tail(minutes)

    points = []
    peaks = []

    for idx, row in tail.iterrows():
        val = int(row["total"]) if pd.notna(row["total"]) else 0
        is_peak = bool(row.get("is_peak_auto", False))
        ts_iso = idx.isoformat()

        point = {
            "label": idx.strftime("%H:%M"),  # đã là UTC+7 trong load_traffic_df
            "value": val,
            "is_peak": is_peak,
            "timestamp": ts_iso,
        }
        points.append(point)

        if is_peak:
            peaks.append(
                {
                    "label": point["label"],
                    "value": val,
                    "timestamp": ts_iso,
                }
            )

    return JSONResponse(
        {
            "camera_id": camera_id,
            "points": points,
            "peaks": peaks,
            "period": f"{minutes}m",
            "timezone": "Asia/Bangkok (UTC+7)",
        }
    )


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