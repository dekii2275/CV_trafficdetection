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
from datetime import datetime, timedelta

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
    total_motor = 0
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
            total_motor += int(item.get("motor", 0) or 0)
            total_bus += int(item.get("bus", 0) or 0)

    if used_cameras == 0:
        return JSONResponse(
            {
                "error": "No log files for today",
                "date": today.isoformat(),
            },
            status_code=404,
        )

    total_all = total_car + total_truck + total_motor + total_bus

    def _pct(x: int, base: int) -> float:
        return float(x) / base if base > 0 else 0.0

    resp = {
        "date": today.isoformat(),
        "num_cameras": used_cameras,
        "totals": {
            "car": total_car,
            "truck": total_truck,
            "motor": total_motor,
            "bus": total_bus,
            "total_vehicles": total_all,
        },
        "percentages": {
            "car": _pct(total_car, total_all),
            "truck": _pct(total_truck, total_all),
            "motor": _pct(total_motor, total_all),
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

@router.get("/analyze/{camera_id}")
async def get_analyze_stats(camera_id: int):
    """
    API endpoint sử dụng analyze.py để trả về thống kê nâng cao:
    - Phần trăm từng loại xe
    - Phát hiện đỉnh lưu lượng (peak detection)
    - Trung bình động (rolling average)
    - Thống kê tổng hợp
    """
    try:
        import sys
        from pathlib import Path
        
        # Thêm thư mục analysis vào path để import
        analysis_path = Path(__file__).parent.parent.parent.parent / "analysis"
        if str(analysis_path) not in sys.path:
            sys.path.insert(0, str(analysis_path))
        
        from analyze import analyze_pipeline_for_api
        from load_data import DEFAULT_CLASSES
        
        # Đường dẫn đến file stats.json (có thể cần điều chỉnh theo cấu trúc thực tế)
        # Thử nhiều đường dẫn có thể
        possible_paths = [
            Path("data/runtime/stats.json"),
            Path("../data/runtime/stats.json"),
            Path("backend/data/runtime/stats.json"),
        ]
        
        stats_path = None
        for p in possible_paths:
            if p.exists():
                stats_path = str(p)
                break
        
        if stats_path is None:
            # Nếu không tìm thấy stats.json, thử đọc từ log file của camera
            log_dir = Path("logs/traffic_count")
            today = datetime.now()
            date_str = today.strftime("%Y%m%d")
            log_file = log_dir / f"cam{camera_id}_{date_str}.json"
            
            if log_file.exists():
                # Đọc dữ liệu từ log file và chuyển đổi format
                with log_file.open("r", encoding="utf-8") as f:
                    log_data = json.load(f)
                
                # Log file chứa dữ liệu theo giờ (hourly)
                # Chuyển đổi sang format line-delimited JSON cho analyze.py
                # Tạo file tạm thời với format line-delimited JSON
                import tempfile
                import os
                from datetime import datetime as dt
                tmp_fd, tmp_path = tempfile.mkstemp(suffix='.json', text=True)
                try:
                    with os.fdopen(tmp_fd, 'w', encoding='utf-8') as tmp:
                        log_list = log_data if isinstance(log_data, list) else [log_data]
                        now = datetime.now()
                        cutoff_time = now - timedelta(minutes=60)  # 60 phút gần nhất
                        
                        for item in log_list:
                            if isinstance(item, dict) and 'timestamp' in item:
                                # Chuyển đổi timestamp ISO sang unix timestamp
                                ts_str = item.get('timestamp', '')
                                try:
                                    if 'T' in ts_str:
                                        # Xử lý ISO format
                                        ts_clean = ts_str.replace('Z', '+00:00')
                                        if '+' in ts_clean or ts_clean.count('-') > 2:
                                            dt_obj = dt.fromisoformat(ts_clean)
                                        else:
                                            dt_obj = dt.fromisoformat(ts_clean + '+00:00')
                                    else:
                                        dt_obj = dt.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                                    
                                    # Chỉ lấy dữ liệu trong 60 phút gần nhất
                                    if dt_obj.timestamp() < cutoff_time.timestamp():
                                        continue
                                    
                                    unix_ts = dt_obj.timestamp()
                                except Exception as e:
                                    # Bỏ qua record không parse được
                                    continue
                                
                                # Lấy giá trị từ log file
                                car = int(item.get("car", 0) or 0)
                                motor = int(item.get("motor", 0) or 0)
                                bus = int(item.get("bus", 0) or 0)
                                truck = int(item.get("truck", 0) or 0)
                                total = int(item.get("total_vehicles", 0) or 0)
                                
                                # Chỉ ghi record nếu có dữ liệu (total > 0)
                                if total > 0:
                                    # Tạo record theo format line-delimited JSON
                                    record = {
                                        "timestamp": unix_ts,
                                        "counts": {
                                            "car": car,
                                            "motor": motor,
                                            "bus": bus,
                                            "truck": truck
                                        },
                                        "total": total
                                    }
                                    # Ghi từng dòng (line-delimited JSON)
                                    tmp.write(json.dumps(record, ensure_ascii=False) + '\n')
                    stats_path = tmp_path
                except Exception as e:
                    # Cleanup nếu có lỗi
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                    raise e
            
            if stats_path is None:
                return JSONResponse(
                    {"error": "No stats data found", "camera_id": camera_id},
                    status_code=404
                )
        
        # Gọi hàm analyze
        df, records = analyze_pipeline_for_api(
            stats_path=stats_path,
            classes=DEFAULT_CLASSES,
            agg_freq="1min",  # 1 phút
            peak_window=5,
            peak_threshold=None,
            minutes_window=60,  # 60 phút gần nhất
            export=False
        )
        
        if df.empty or len(records) == 0:
            return JSONResponse(
                {
                    "error": "No data to analyze",
                    "camera_id": camera_id,
                    "message": "Không có dữ liệu để phân tích"
                },
                status_code=404
            )
        
        # Tính toán thống kê tổng hợp
        # Lưu ý: df đã được aggregate theo phút từ analyze.py
        total_records = len(records)
        
        # Tính tổng số xe: sum tất cả các giá trị trong khoảng thời gian
        # Với dữ liệu đã được resample, ta cần sum các giá trị
        # Lọc bỏ các giá trị 0 (có thể là do resample fillna) để tính chính xác hơn
        if 'total' in df.columns and len(df) > 0:
            # Lọc các record có dữ liệu thực (total > 0)
            non_zero_df = df[df['total'] > 0]
            if len(non_zero_df) > 0:
                # Tính tổng từ các record có dữ liệu
                total_vehicles = int(non_zero_df['total'].sum())
            else:
                # Nếu không có record nào > 0, tính tổng tất cả
                total_vehicles = int(df['total'].sum())
        else:
            total_vehicles = 0
        
        # Tính tổng từng loại xe - sum tất cả các giá trị trong khoảng thời gian
        vehicle_totals = {}
        vehicle_percentages = {}
        
        # Lọc dataframe có dữ liệu để tính chính xác
        non_zero_df = df[df['total'] > 0] if 'total' in df.columns and len(df) > 0 else df
        
        for cls in DEFAULT_CLASSES:
            if cls in df.columns:
                # Sum tất cả giá trị của loại xe đó trong khoảng thời gian
                # Ưu tiên tính trên các record có dữ liệu (non_zero_df)
                if len(non_zero_df) > 0 and cls in non_zero_df.columns:
                    vehicle_totals[cls] = int(non_zero_df[cls].sum())
                else:
                    vehicle_totals[cls] = int(df[cls].sum())
            else:
                vehicle_totals[cls] = 0
        
        # Tính phần trăm dựa trên tổng số xe
        if total_vehicles > 0:
            for cls in DEFAULT_CLASSES:
                vehicle_percentages[cls] = round((vehicle_totals[cls] / total_vehicles) * 100, 2)
        else:
            for cls in DEFAULT_CLASSES:
                vehicle_percentages[cls] = 0.0
        
        # Phát hiện đỉnh
        peak_count = int(df['is_peak_auto'].sum()) if 'is_peak_auto' in df.columns else 0
        
        # Tính trung bình, min, max
        stats_summary = {
            "mean": float(df['total'].mean()) if 'total' in df.columns else 0.0,
            "min": int(df['total'].min()) if 'total' in df.columns else 0,
            "max": int(df['total'].max()) if 'total' in df.columns else 0,
            "std": float(df['total'].std()) if 'total' in df.columns else 0.0,
        }
        
        # Rolling average (nếu có)
        rolling_mean = None
        if 'rolling_mean' in df.columns:
            rolling_mean = df['rolling_mean'].tolist()[-10:]  # 10 giá trị cuối
        
        response = {
            "camera_id": camera_id,
            "summary": {
                "total_records": total_records,
                "total_vehicles": int(total_vehicles),
                "vehicle_totals": vehicle_totals,
                "vehicle_percentages": vehicle_percentages,
                "peak_detections": peak_count,
                "stats": stats_summary,
            },
            "time_series": records[-30:],  # 30 bản ghi cuối cùng
            "rolling_mean": rolling_mean,
        }
        
        # Cleanup temp file nếu có
        if stats_path and stats_path.startswith('/tmp') or 'tmp' in stats_path:
            try:
                import os
                os.unlink(stats_path)
            except:
                pass
        
        return JSONResponse(response)
        
    except ImportError as e:
        print(f"[get_analyze_stats] Import error: {e}")
        return JSONResponse(
            {"error": "Analysis module not available", "detail": str(e)},
            status_code=500
        )
    except Exception as e:
        print(f"[get_analyze_stats] Error for camera {camera_id}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"error": "Internal server error", "detail": str(e)},
            status_code=500
        )
