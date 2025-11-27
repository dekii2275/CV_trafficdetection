import os
import cv2
import numpy as np
from datetime import datetime
from ultralytics import YOLO
import yt_dlp
import json
from pathlib import Path

from app.core.config import settings_metric_transport

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# ============================================================
# 1. LẤY DIRECT STREAM YOUTUBE
# ============================================================
def get_stream_url(youtube_url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if info and "url" in info:
                print("✅ Lấy stream YouTube thành công.")
                return info["url"]
    except Exception as e:
        print(f"❌ Lỗi lấy link YouTube: {e}")
    return None


# ============================================================
# 2. CLASS ĐẾM XE - SIMPLE JSON FORMAT
# ============================================================
class AnalyzeOnRoadBase:
    """
    Logic đếm xe với tự động lưu JSON mỗi 1 phút (format đơn giản)
    """

    def __init__(self, video_index=0, show=True, count_conf=0.4, 
                 auto_save=True, save_interval_seconds=60):

        self.path_video = settings_metric_transport.PATH_VIDEOS[video_index]
        self.model_path = settings_metric_transport.MODELS_PATH
        self.device = settings_metric_transport.DEVICE
        self.video_index = video_index

        # ===== ROI từ config =====
        self.roi_pts = settings_metric_transport.REGIONS[video_index].astype(np.int32)
        self.roi_pts = self.roi_pts.reshape((-1, 1, 2))

        self.show = show
        self.count_conf = count_conf

        # ===== AUTO SAVE CONFIG =====
        self.auto_save = auto_save
        self.save_interval_seconds = save_interval_seconds
        self.last_save_time = datetime.now()
        self.session_start_time = datetime.now()
        
        # Tạo thư mục logs
        self.logs_dir = Path("logs/traffic_count")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # File log cho session hiện tại
        session_id = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        self.json_file = self.logs_dir / f"traffic_count_camera{video_index}_{session_id}.json"
        
        print(f"📁 JSON output: {self.json_file}")

        # ===== Load YOLO =====
        self.model = YOLO(self.model_path)
        print(f"✅ Loaded model: {self.model_path}")
        print(f"✅ Device: {self.device}")
        print(f"✅ Auto-save: {'ON' if auto_save else 'OFF'} (every {save_interval_seconds}s)")

        # ===== STATE =====
        self.tracked_objects = {}
        self.counted_ids = {}
        self.count_entering = {}
        self.count_exiting = {}
        
        # FPS tracking
        self.current_fps = 0.0

    def _is_inside_roi(self, cx, cy):
        """Kiểm tra điểm có trong ROI polygon"""
        result = cv2.pointPolygonTest(self.roi_pts, (float(cx), float(cy)), False)
        return result >= 0

    def _count_objects(self, boxes, classes, confs, ids, names):
        """Logic đếm xe khi cross qua ROI boundary"""
        if ids is None:
            return

        current_frame_ids = set()

        for i in range(len(boxes)):
            if confs[i] < self.count_conf:
                continue

            x1, y1, x2, y2 = boxes[i]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            obj_id = int(ids[i])
            class_name = names[int(classes[i])]

            is_inside_now = self._is_inside_roi(cx, cy)
            
            # Bỏ qua xe ngoài ROI hoàn toàn
            if obj_id not in self.tracked_objects and not is_inside_now:
                continue
            
            current_frame_ids.add(obj_id)

            # Lần đầu thấy object
            if obj_id not in self.tracked_objects:
                self.tracked_objects[obj_id] = {
                    'prev_cx': cx,
                    'prev_cy': cy,
                    'was_inside': is_inside_now,
                    'class': class_name
                }
                
                if is_inside_now:
                    if class_name not in self.counted_ids:
                        self.counted_ids[class_name] = set()
                        self.count_entering[class_name] = set()
                    
                    if obj_id not in self.counted_ids[class_name]:
                        self.counted_ids[class_name].add(obj_id)
                        self.count_entering[class_name].add(obj_id)
                        print(f"✅ [{class_name}] ID={obj_id} ENTERED ROI")
                
                continue

            prev_state = self.tracked_objects[obj_id]
            was_inside_before = prev_state['was_inside']

            # Xe đi từ ngoài vào trong
            if not was_inside_before and is_inside_now:
                if class_name not in self.counted_ids:
                    self.counted_ids[class_name] = set()
                    self.count_entering[class_name] = set()
                
                if obj_id not in self.counted_ids[class_name]:
                    self.counted_ids[class_name].add(obj_id)
                    self.count_entering[class_name].add(obj_id)
                    print(f"✅ [{class_name}] ID={obj_id} ENTERED ROI")

            # Xe đi từ trong ra ngoài
            elif was_inside_before and not is_inside_now:
                if class_name not in self.count_exiting:
                    self.count_exiting[class_name] = set()
                
                if obj_id not in self.count_exiting[class_name]:
                    self.count_exiting[class_name].add(obj_id)
                    print(f"⬅️ [{class_name}] ID={obj_id} EXITED ROI")

            # Cập nhật state
            self.tracked_objects[obj_id] = {
                'prev_cx': cx,
                'prev_cy': cy,
                'was_inside': is_inside_now,
                'class': class_name
            }

        # Cleanup
        tracked_ids = set(self.tracked_objects.keys())
        lost_ids = tracked_ids - current_frame_ids
        for lost_id in lost_ids:
            del self.tracked_objects[lost_id]

    def _save_json_record(self):
        """Lưu bản ghi JSON theo format đơn giản"""
        current_time = datetime.now()
        
        # Tạo counts dict
        counts = {}
        for class_name in self.counted_ids.keys():
            counts[class_name] = len(self.counted_ids[class_name])
        
        # Tính tổng
        total = sum(counts.values())
        
        # Tạo record theo format yêu cầu
        record = {
            "timestamp": current_time.timestamp(),
            "fps": round(self.current_fps, 1),
            "counts": counts,
            "total": total
        }
        
        # Lưu vào file (append mode, mỗi dòng 1 JSON)
        try:
            with open(self.json_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
            
            print(f"💾 [{current_time.strftime('%H:%M:%S')}] Saved: total={total}, fps={record['fps']}")
            
            # In chi tiết
            if counts:
                details = ", ".join([f"{k}:{v}" for k, v in counts.items()])
                print(f"   📊 {details}")
            else:
                print("   📊 No vehicles counted yet")
                
        except Exception as e:
            print(f"❌ Error saving JSON: {e}")
        
        self.last_save_time = current_time

    def _check_and_save(self):
        """Kiểm tra và lưu nếu đã đủ thời gian"""
        if not self.auto_save:
            return
        
        current_time = datetime.now()
        elapsed = (current_time - self.last_save_time).total_seconds()
        
        if elapsed >= self.save_interval_seconds:
            self._save_json_record()

    def process_single_frame(self, frame):
        """Xử lý 1 frame video"""
        
        results = self.model.track(
            frame,
            persist=True,
            device=self.device,
            conf=0.25,
            iou=0.5,
            verbose=False,
        )

        r = results[0]
        plotted = r.plot()

        # Vẽ vùng ROI
        cv2.polylines(plotted, [self.roi_pts], isClosed=True,
                      color=(0, 255, 255), thickness=3)
        
        roi_center = self.roi_pts.mean(axis=0)[0].astype(int)
        cv2.putText(plotted, "ROI ZONE", 
                    tuple(roi_center), 
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 255), 2)

        # Lấy detections và count
        if r.boxes is not None and len(r.boxes) > 0:
            boxes = r.boxes.xyxy.cpu().numpy()
            classes = r.boxes.cls.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()
            ids = (
                r.boxes.id.cpu().numpy().astype(int)
                if r.boxes.id is not None else None
            )
            self._count_objects(boxes, classes, confs, ids, r.names)

        # ===== HIỂN THỊ KẾT QUẢ ĐẾM =====
        y_offset = 30
        line_height = 30
        x_pos = 10

        cv2.putText(plotted, "=== VEHICLE COUNT ===",
                    (x_pos, y_offset), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 0), 2)
        y_offset += line_height

        total_count = 0
        if self.counted_ids:
            for cls_name in sorted(self.counted_ids.keys()):
                count = len(self.counted_ids[cls_name])
                total_count += count
                
                text = f"{cls_name}: {count}"
                cv2.putText(plotted, text,
                            (x_pos, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)
                y_offset += line_height
            
            # Hiển thị tổng
            cv2.putText(plotted, f"TOTAL: {total_count}",
                        (x_pos, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 255), 2)
        else:
            cv2.putText(plotted, "No vehicles counted yet",
                        (x_pos, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 165, 255), 2)

        # Hiển thị countdown đến lần save tiếp theo
        if self.auto_save:
            time_since_save = (datetime.now() - self.last_save_time).total_seconds()
            time_to_next = int(self.save_interval_seconds - time_since_save)
            
            cv2.putText(plotted, f"Next save: {time_to_next}s",
                       (plotted.shape[1] - 180, 20),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 255, 0), 2)

        return plotted

    def process_video(self):
        """Xử lý video stream"""
        
        stream_url = get_stream_url(self.path_video)
        if not stream_url:
            print("❌ Không thể mở livestream.")
            return

        cam = cv2.VideoCapture(stream_url)
        if not cam.isOpened():
            print("❌ Không mở được video.")
            return

        print("🎬 Bắt đầu đếm xe trong ROI...")
        print("🔴 Press 'q' to quit, 's' to save now")

        frame_count = 0
        
        try:
            while True:
                t0 = datetime.now()

                ok, frame = cam.read()
                if not ok:
                    print("⚠️ Không đọc được frame")
                    break

                frame = cv2.resize(frame, (640, 360))
                plotted = self.process_single_frame(frame)

                # Kiểm tra và lưu JSON tự động
                self._check_and_save()

                # Tính FPS
                fps = 1 / ((datetime.now() - t0).total_seconds() + 1e-6)
                self.current_fps = fps

                cv2.putText(plotted, f"FPS: {int(fps)}",
                            (plotted.shape[1] - 100, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 100), 2)

                frame_count += 1

                if self.show:
                    cv2.imshow("Traffic Count - Simple JSON Output", plotted)
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord("q"):
                        break
                    elif key == ord("s"):
                        print("💾 Manual save triggered...")
                        self._save_json_record()

        finally:
            # Lưu lần cuối trước khi thoát
            if self.auto_save:
                print("\n💾 Saving final record before exit...")
                self._save_json_record()
            
            cam.release()
            if self.show:
                cv2.destroyAllWindows()
            
            self._print_summary()

    def _print_summary(self):
        """In báo cáo tổng kết"""
        print("\n" + "="*60)
        print("📊 TRAFFIC COUNT SUMMARY")
        print("="*60)
        
        if not self.counted_ids:
            print("❌ No vehicles counted")
            return
        
        total_vehicles = sum(len(ids) for ids in self.counted_ids.values())
        print(f"Total Vehicles: {total_vehicles}")
        print("-"*60)
        
        for cls_name in sorted(self.counted_ids.keys()):
            count = len(self.counted_ids[cls_name])
            print(f"{cls_name:15s}: {count:3d}")
        
        # Session info
        elapsed = datetime.now() - self.session_start_time
        hours, remainder = divmod(elapsed.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print(f"\nSession duration: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        print(f"📁 JSON file: {self.json_file}")
        print("="*60 + "\n")


# ============================================================
# RUN TRỰC TIẾP
# ============================================================
if __name__ == "__main__":
    analyzer = AnalyzeOnRoadBase(
        video_index=0,
        show=True,
        auto_save=True,
        save_interval_seconds=60  # Lưu mỗi 60 giây (1 phút)
    )
    analyzer.process_video()