import cv2
import numpy as np
from datetime import datetime
from ultralytics import YOLO
import yt_dlp
from pathlib import Path
import traceback
import time
from app.core.config import settings_metric_transport
import os
# ✅ Import Database
from app.db.base import SessionLocal
from app.models.traffic_logs import TrafficLog

class AnalyzeOnRoadBase:
    """
    Traffic Counter Base Class - BALANCED QUALITY VERSION (480p Processing / 720p Input)
    """

    def __init__(self, video_index=0, shared_dict=None, result_queue=None,
                 show=False, count_conf=0.4, frame_dict=None,
                 auto_save=True, save_interval_seconds=60):

        # --- Validation ---
        if video_index >= len(settings_metric_transport.PATH_VIDEOS):
            raise ValueError(f"Video index {video_index} out of range.")
        
        # --- Config ---
        self.video_index = video_index
        self.path_video = settings_metric_transport.PATH_VIDEOS[video_index]
        self.model_path = settings_metric_transport.MODELS_PATH
        self.device = settings_metric_transport.DEVICE
        raw_roi = settings_metric_transport.REGIONS[video_index]
        self.roi_pts = np.array(raw_roi, dtype=np.int32).reshape((-1, 1, 2))

        # --- Shared Data ---
        self.shared_dict = shared_dict
        self.frame_dict = frame_dict    
        self.result_queue = result_queue
        self.show = show
        self.count_conf = count_conf

        # ===== 🚀 CẤU HÌNH CHẤT LƯỢNG (Đã Nâng Cấp) =====
        self.skip_frames = 3       # Giữ nguyên 3 để cân bằng tải
        
        # Tăng kích thước xử lý (Trước là 480x270 -> Mờ)
        # 854x480 là chuẩn 480p (Widescreen), đủ nét để đọc biển số gần
        self.process_width = 854   
        self.process_height = 480  
        
        self.last_result = None
        
        # ===== Auto Save =====
        self.auto_save = auto_save
        self.save_interval_seconds = save_interval_seconds
        self.last_save_time = datetime.now()
        self.session_start_time = datetime.now()
        
        self.logs_dir = Path("logs/traffic_count")
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.current_day = datetime.now().date()

        # ===== Model Loading =====
        try:
            self.model = YOLO(self.model_path)
            print(f"[Camera {video_index}] ✅ Model loaded")
        except Exception as e:
            print(f"[Camera {video_index}] ❌ Model load failed: {e}")
            raise

        # ===== Tracking State =====
        self.tracked_objects = {}
        self.counted_ids = {}
        self.count_entering = {}
        self.count_exiting = {}
        self.current_in_roi = {}
        self.current_fps = 0.0
        self.frame_count = 0
        self.is_running = True

    # --- Helper Methods ---
    def _is_inside_roi(self, cx, cy):
        return cv2.pointPolygonTest(self.roi_pts, (float(cx), float(cy)), False) >= 0

    def _update_set(self, data_dict, class_name, obj_id):
        if class_name not in data_dict: data_dict[class_name] = set()
        data_dict[class_name].add(obj_id)

    def _count_objects(self, boxes, classes, confs, ids, names):
        if ids is None:
            self.current_in_roi = {}
            return
        current_frame_ids = set()
        temp_current_in_roi = {}
        for i in range(len(boxes)):
            if confs[i] < self.count_conf: continue
            x1, y1, x2, y2 = boxes[i]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            obj_id = int(ids[i])
            class_name = names[int(classes[i])]
            is_inside_now = self._is_inside_roi(cx, cy)
            
            if is_inside_now: temp_current_in_roi[class_name] = temp_current_in_roi.get(class_name, 0) + 1
            if obj_id not in self.tracked_objects and not is_inside_now: continue
            
            current_frame_ids.add(obj_id)
            if obj_id not in self.tracked_objects:
                self.tracked_objects[obj_id] = {'was_inside': is_inside_now, 'class': class_name}
                if is_inside_now:
                    self._update_set(self.counted_ids, class_name, obj_id)
                    self._update_set(self.count_entering, class_name, obj_id)
                continue

            prev_state = self.tracked_objects[obj_id]
            if not prev_state['was_inside'] and is_inside_now:
                self._update_set(self.counted_ids, class_name, obj_id)
                self._update_set(self.count_entering, class_name, obj_id)
            elif prev_state['was_inside'] and not is_inside_now:
                self._update_set(self.count_exiting, class_name, obj_id)
            self.tracked_objects[obj_id]['was_inside'] = is_inside_now
            self.tracked_objects[obj_id]['class'] = class_name
        self.current_in_roi = temp_current_in_roi
        tracked_ids = set(self.tracked_objects.keys())
        lost_ids = tracked_ids - current_frame_ids
        for lost_id in lost_ids: del self.tracked_objects[lost_id]

    def _update_shared_data(self):
        if self.shared_dict is None: return
        try:
            # Lấy hợp tất cả các key để đảm bảo không sót loại xe nào
            all_classes = set(self.counted_ids.keys()) | set(self.current_in_roi.keys())
            total_entered = sum(len(self.counted_ids.get(cls, set())) for cls in all_classes)
            total_current = sum(self.current_in_roi.get(cls, 0) for cls in all_classes)
            
            key = f"camera_{self.video_index}"
            self.shared_dict[key] = {
                'fps': round(self.current_fps, 1),
                'total_entered': total_entered,
                'total_current': total_current,
                'timestamp': datetime.now().timestamp(),
                'details': {cls: {'entered': len(self.counted_ids.get(cls, set())), 'current': self.current_in_roi.get(cls, 0)} for cls in all_classes}
            }
        except Exception: pass

    def _check_and_save(self):
        """Auto-save thống kê vào PostgreSQL database."""
        if not self.auto_save: return

        now = datetime.now()
        if (now - self.last_save_time).total_seconds() < self.save_interval_seconds:
            return

        # Tính toán số lượng
        car_count = len(self.counted_ids.get("car", set()))
        
        # Gộp tất cả biến thể xe máy
        motor_ids = set()
        motor_ids |= self.counted_ids.get("motor", set())
        motor_ids |= self.counted_ids.get("bike", set())
        motor_ids |= self.counted_ids.get("motorbike", set())
        motor_ids |= self.counted_ids.get("motorcycle", set())
        motor_count = len(motor_ids)

        bus_count = len(self.counted_ids.get("bus", set()))
        truck_count = len(self.counted_ids.get("truck", set()))
        total_vehicles = car_count + motor_count + bus_count + truck_count

        # Ghi vào DB
        db = SessionLocal()
        try:
            log = TrafficLog(
                camera_id=self.video_index,
                timestamp=now,
                count_car=int(car_count),
                count_motor=int(motor_count),
                count_bus=int(bus_count),
                count_truck=int(truck_count),
                total_vehicles=int(total_vehicles),
                fps=round(self.current_fps, 1)
            )
            db.add(log)
            db.commit()
            self.last_save_time = now
        except Exception as e:
            print(f"[Cam {self.video_index}] ❌ Error saving DB: {e}")
            db.rollback()
        finally:
            db.close()

    def process_single_frame(self, frame):
        # Logic Skip Frame
        if self.frame_count % self.skip_frames == 0:
            results = self.model.track(frame, persist=True, device=self.device, conf=0.25, iou=0.5, verbose=False)
            r = results[0]
            self.last_result = r
            if r.boxes is not None and len(r.boxes) > 0:
                boxes = r.boxes.xyxy.cpu().numpy()
                classes = r.boxes.cls.cpu().numpy().astype(int)
                confs = r.boxes.conf.cpu().numpy()
                ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else None
                self._count_objects(boxes, classes, confs, ids, r.names)
            else: self.current_in_roi = {}
            plotted = r.plot()
        else:
            if self.last_result is not None: plotted = self.last_result.plot(img=frame)
            else: plotted = frame
        
        cv2.polylines(plotted, [self.roi_pts], isClosed=True, color=(0, 255, 255), thickness=2)
        return plotted

    def get_stream_url(self, youtube_url):
        """Lấy stream URL 720p với cookies"""
        try:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            cookie_path = base_dir / "cookies.txt"
        except:
            cookie_path = Path("cookies.txt")

        if cookie_path.exists():
            print(f"[Camera {self.video_index}] 🍪 Đã tìm thấy Cookies tại: {cookie_path}")
        else:
            print(f"[Camera {self.video_index}] ⚠️ CẢNH BÁO: Không tìm thấy cookies.txt")

        ydl_opts = {
            "quiet": True, 
            "no_warnings": True,
            # 🔥 NÂNG CẤP: Lấy video tốt nhất <= 720p (Nét hơn 360p rất nhiều)
            "format": "best[height<=720]", 
            "nocheckcertificate": True,
            "cookiefile": str(cookie_path) if cookie_path.exists() else None,
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                if info and "url" in info: 
                    return info["url"]
        except Exception as e:
            print(f"[Camera {self.video_index}] ❌ Lỗi lấy link: {e}")
            
        return youtube_url

    def process_video(self):
        print(f"[Camera {self.video_index}] 🎬 START MONITORING (720p Input, 480p Process)")
        while self.is_running:
            try:
                stream_url = self.get_stream_url(self.path_video)
                cam = cv2.VideoCapture(stream_url)
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not cam.isOpened():
                    print(f"[Cam {self.video_index}] Retry in 3s...")
                    time.sleep(3)
                    continue
                
                print(f"[Cam {self.video_index}] ✅ Connected!")

                while self.is_running:
                    t0 = datetime.now()
                    ok, frame = cam.read()
                    if not ok: break 

                    # 🔥 NÂNG CẤP: Resize to hơn (854x480) để nhìn rõ hơn
                    frame = cv2.resize(frame, (self.process_width, self.process_height))
                    plotted = self.process_single_frame(frame)

                    # 🔥 NÂNG CẤP: Gửi ảnh API với chất lượng 65% (Đẹp hơn mức 30 cũ)
                    if self.frame_dict is not None:
                        try:
                            _, buffer = cv2.imencode('.jpg', plotted, [cv2.IMWRITE_JPEG_QUALITY, 65])
                            self.frame_dict[f"camera_{self.video_index}"] = buffer.tobytes()
                        except Exception: pass

                    self.frame_count += 1
                    self._update_shared_data()
                    self._check_and_save()

                    delta = (datetime.now() - t0).total_seconds()
                    self.current_fps = 1 / (delta + 1e-6)

                    if self.show:
                        cv2.imshow(f"Cam {self.video_index}", plotted)
                        if cv2.waitKey(1) & 0xFF == ord('q'): 
                            self.is_running = False
                            break
                cam.release()
            except Exception as e:
                print(f"[Cam {self.video_index}] Error: {e}")
                time.sleep(2)
        if self.show: cv2.destroyAllWindows()

def main():
    """Chạy thử 1 camera"""
    analyzer = AnalyzeOnRoadBase(
        video_index=0,
        shared_dict=None,
        result_queue=None,
        show=True,
        frame_dict=None,
        auto_save=True,
        save_interval_seconds=5
    )
    try:
        analyzer.process_video()
    except KeyboardInterrupt:
        analyzer.is_running = False

if __name__ == "__main__":
    main()