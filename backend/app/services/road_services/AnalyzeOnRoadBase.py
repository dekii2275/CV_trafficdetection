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
    Logic đếm xe nâng cao: 
    - Total Flow (Vào/Ra)
    - Current Density (Mật độ hiện tại trong vùng)
    - Auto Save JSON logs
    """

    def __init__(self, video_index=0, show=True, count_conf=0.4, 
                 auto_save=True, save_interval_seconds=60):

        # --- Cấu hình cơ bản ---
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

        # ===== STATE VARIABLES =====
        # Lưu trạng thái của từng object ID: {id: {prev_cx, prev_cy, was_inside, class}}
        self.tracked_objects = {}
        
        # Set chứa các ID đã đếm được (để tính tổng Unique)
        self.counted_ids = {}     # {class_name: set(ids)}
        
        # Set chứa ID xe đã đi vào
        self.count_entering = {}  # {class_name: set(ids)}
        
        # Set chứa ID xe đã đi ra
        self.count_exiting = {}   # {class_name: set(ids)}
        
        # Số lượng xe ĐANG ở trong vùng (reset mỗi frame)
        self.current_in_roi = {}  # {class_name: int_count}
        
        # FPS tracking
        self.current_fps = 0.0

    def _is_inside_roi(self, cx, cy):
        """Kiểm tra điểm có trong ROI polygon"""
        result = cv2.pointPolygonTest(self.roi_pts, (float(cx), float(cy)), False)
        return result >= 0

    def _update_set(self, data_dict, class_name, obj_id):
        """Helper để thêm ID vào dict của set an toàn"""
        if class_name not in data_dict:
            data_dict[class_name] = set()
        data_dict[class_name].add(obj_id)

    def _count_objects(self, boxes, classes, confs, ids, names):
        """Logic đếm xe chính"""
        if ids is None:
            self.current_in_roi = {} # Không có xe nào
            return

        current_frame_ids = set()
        
        # Biến tạm để đếm số xe đang trong vùng ở frame này
        temp_current_in_roi = {}

        for i in range(len(boxes)):
            if confs[i] < self.count_conf:
                continue

            x1, y1, x2, y2 = boxes[i]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            obj_id = int(ids[i])
            class_name = names[int(classes[i])]

            is_inside_now = self._is_inside_roi(cx, cy)
            
            # --- 1. CẬP NHẬT MẬT ĐỘ TỨC THỜI ---
            if is_inside_now:
                temp_current_in_roi[class_name] = temp_current_in_roi.get(class_name, 0) + 1

            # --- 2. LỌC OBJECT ---
            # Nếu xe ở ngoài ROI và chưa từng được track, bỏ qua để tối ưu
            if obj_id not in self.tracked_objects and not is_inside_now:
                continue
            
            current_frame_ids.add(obj_id)

            # --- 3. LOGIC TRACKING TRẠNG THÁI ---
            
            # a) Lần đầu tiên nhìn thấy object này
            if obj_id not in self.tracked_objects:
                self.tracked_objects[obj_id] = {
                    'was_inside': is_inside_now,
                    'class': class_name
                }
                # Nếu spawn ra ngay trong vùng -> Tính là Entering
                if is_inside_now:
                    self._update_set(self.counted_ids, class_name, obj_id)
                    self._update_set(self.count_entering, class_name, obj_id)
                    print(f"✅ [{class_name}] ID={obj_id} ENTERED (Spawned inside)")
                continue

            # b) Object đã tồn tại, kiểm tra chuyển trạng thái
            prev_state = self.tracked_objects[obj_id]
            was_inside_before = prev_state['was_inside']

            # Vào vùng (Outside -> Inside)
            if not was_inside_before and is_inside_now:
                self._update_set(self.counted_ids, class_name, obj_id)
                self._update_set(self.count_entering, class_name, obj_id)
                print(f"✅ [{class_name}] ID={obj_id} ENTERED ROI")

            # Ra vùng (Inside -> Outside)
            elif was_inside_before and not is_inside_now:
                self._update_set(self.count_exiting, class_name, obj_id)
                print(f"⬅️ [{class_name}] ID={obj_id} EXITED ROI")

            # Cập nhật trạng thái mới
            self.tracked_objects[obj_id]['was_inside'] = is_inside_now
            self.tracked_objects[obj_id]['class'] = class_name

        # Cập nhật biến mật độ của class
        self.current_in_roi = temp_current_in_roi

        # Cleanup: Xóa các object không còn xuất hiện trong frame hiện tại
        tracked_ids = set(self.tracked_objects.keys())
        lost_ids = tracked_ids - current_frame_ids
        for lost_id in lost_ids:
            del self.tracked_objects[lost_id]

    def _save_json_record(self):
        """Lưu bản ghi JSON chi tiết"""
        current_time = datetime.now()
        
        # Lấy danh sách tất cả các loại xe đã thấy
        all_classes = set(self.counted_ids.keys()) | \
                      set(self.count_exiting.keys()) | \
                      set(self.current_in_roi.keys())

        details = {}
        total_entered = 0
        total_exited = 0
        total_current = 0

        for cls in all_classes:
            n_enter = len(self.counted_ids.get(cls, set()))
            n_exit = len(self.count_exiting.get(cls, set()))
            n_curr = self.current_in_roi.get(cls, 0)
            
            details[cls] = {
                "entered": n_enter,
                "exited": n_exit,
                "current_density": n_curr
            }
            
            total_entered += n_enter
            total_exited += n_exit
            total_current += n_curr

        record = {
            "timestamp": current_time.timestamp(),
            "readable_time": current_time.strftime('%Y-%m-%d %H:%M:%S'),
            "fps": round(self.current_fps, 1),
            "summary": {
                "total_entered": total_entered,
                "total_exited": total_exited,
                "current_in_zone": total_current
            },
            "details": details
        }
        
        try:
            with open(self.json_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
            
            print(f"💾 Saved: Entered={total_entered}, Current={total_current}, FPS={record['fps']}")
        except Exception as e:
            print(f"❌ Error saving JSON: {e}")
        
        self.last_save_time = current_time

    def _check_and_save(self):
        """Kiểm tra thời gian để lưu file"""
        if not self.auto_save:
            return
        
        elapsed = (datetime.now() - self.last_save_time).total_seconds()
        if elapsed >= self.save_interval_seconds:
            self._save_json_record()

    def _draw_hud(self, frame):
        """Vẽ bảng thông tin chi tiết lên màn hình"""
        # Tạo overlay màu tối để text dễ đọc
        overlay = frame.copy()
        panel_w = 300
        panel_h = 300
        cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (0, 0, 0), -1)
        # Apply độ trong suốt
        alpha = 0.6
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Config Font
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thick = 1
        text_color = (255, 255, 255)
        
        x_start = 10
        y_start = 20
        line_h = 25

        # 1. Header
        cv2.putText(frame, "TRAFFIC MONITOR SYSTEM", (x_start, y_start), font, 0.6, (0, 255, 255), 2)
        y_start += 30
        
        # 2. Status Line
        if self.auto_save:
            remain = int(self.save_interval_seconds - (datetime.now() - self.last_save_time).total_seconds())
            status_txt = f"FPS: {int(self.current_fps)} | Save in: {remain}s"
        else:
            status_txt = f"FPS: {int(self.current_fps)} | Auto-save: OFF"
        cv2.putText(frame, status_txt, (x_start, y_start), font, 0.5, (0, 255, 100), 1)
        y_start += 20
        
        # 3. Table Header
        cv2.line(frame, (x_start, y_start), (panel_w - 10, y_start), (200, 200, 200), 1)
        y_start += 20
        header = f"{'TYPE':<8} {'IN':<4} {'OUT':<4} {'NOW':<4}"
        cv2.putText(frame, header, (x_start, y_start), font, font_scale, (200, 200, 200), 1)
        y_start += 10
        cv2.line(frame, (x_start, y_start), (panel_w - 10, y_start), (100, 100, 100), 1)
        y_start += 20

        # 4. Table Content
        all_classes = set(self.counted_ids.keys()) | set(self.current_in_roi.keys())
        
        grand_total_in = 0
        grand_total_now = 0

        if not all_classes:
            cv2.putText(frame, "Waiting for vehicles...", (x_start, y_start), font, font_scale, (150, 150, 150), 1)
            y_start += line_h
        else:
            for cls in sorted(all_classes):
                c_in = len(self.counted_ids.get(cls, []))
                c_out = len(self.count_exiting.get(cls, []))
                c_now = self.current_in_roi.get(cls, 0)
                
                grand_total_in += c_in
                grand_total_now += c_now

                # Highlight dòng có xe đang ở trong
                row_color = (0, 255, 0) if c_now > 0 else (200, 200, 200)
                
                # Format text canh lề
                row_text = f"{cls[:8]:<8} {c_in:<4} {c_out:<4} {c_now:<4}"
                cv2.putText(frame, row_text, (x_start, y_start), font, font_scale, row_color, 1)
                y_start += line_h

        # 5. Summary Footer
        cv2.line(frame, (x_start, y_start-10), (panel_w - 10, y_start-10), (100, 100, 100), 1)
        cv2.putText(frame, f"TOTAL ENTERED: {grand_total_in}", (x_start, y_start), font, 0.6, (0, 255, 255), 1)
        y_start += 25
        cv2.putText(frame, f"CURRENT DENSITY: {grand_total_now}", (x_start, y_start), font, 0.6, (0, 165, 255), 2)

    def process_single_frame(self, frame):
        """Xử lý 1 frame video"""
        
        # Tracking YOLO
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
                      color=(0, 255, 255), thickness=2)
        
        # Label ROI
        roi_center = self.roi_pts.mean(axis=0)[0].astype(int)
        cv2.putText(plotted, "DETECTION ZONE", tuple(roi_center), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # Xử lý kết quả Detection
        if r.boxes is not None and len(r.boxes) > 0:
            boxes = r.boxes.xyxy.cpu().numpy()
            classes = r.boxes.cls.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()
            ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else None
            
            self._count_objects(boxes, classes, confs, ids, r.names)
        else:
            self.current_in_roi = {} # Reset nếu không bắt được gì

        # Vẽ bảng thông tin (HUD)
        self._draw_hud(plotted)

        return plotted

    def process_video(self):
        """Main Loop xử lý video stream"""
        
        stream_url = get_stream_url(self.path_video)
        if not stream_url:
            # Fallback nếu không lấy được link (ví dụ dùng webcam hoặc file local)
            print("⚠️ Không lấy được link Youtube, thử dùng đường dẫn gốc...")
            stream_url = self.path_video

        cam = cv2.VideoCapture(stream_url)
        if not cam.isOpened():
            print("❌ Không thể mở nguồn video.")
            return

        print("🎬 START MONITORING...")
        print(f"🎯 ROI Zone: {self.roi_pts.tolist()}")
        print("🔴 Press 'q' to quit, 's' to save manually")

        try:
            while True:
                t0 = datetime.now()

                ok, frame = cam.read()
                if not ok:
                    print("⚠️ End of stream / Cannot read frame")
                    break

                # Resize để xử lý nhanh hơn
                frame = cv2.resize(frame, (640, 360))
                
                # Core Processing
                plotted = self.process_single_frame(frame)

                # Auto Save Check
                self._check_and_save()

                # FPS Calc
                delta = (datetime.now() - t0).total_seconds()
                self.current_fps = 1 / (delta + 1e-6)

                if self.show:
                    cv2.imshow("Advanced Traffic Counter", plotted)
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord("q"):
                        break
                    elif key == ord("s"):
                        print("💾 Manual save triggered...")
                        self._save_json_record()

        except KeyboardInterrupt:
            print("\n🛑 Stopped by user.")
        finally:
            # Lưu lần cuối trước khi thoát
            if self.auto_save:
                print("💾 Saving final record before exit...")
                self._save_json_record()
            
            cam.release()
            if self.show:
                cv2.destroyAllWindows()
            
            self._print_summary()

    def _print_summary(self):
        """In báo cáo tổng kết ra terminal"""
        print("\n" + "="*60)
        print("📊 SESSION SUMMARY")
        print("="*60)
        
        all_classes = set(self.counted_ids.keys()) | set(self.count_exiting.keys())
        
        if not all_classes:
            print("❌ No vehicles recorded.")
        else:
            print(f"{'TYPE':<15} {'ENTERED':<10} {'EXITED':<10}")
            print("-" * 40)
            total_in = 0
            for cls in sorted(all_classes):
                n_in = len(self.counted_ids.get(cls, []))
                n_out = len(self.count_exiting.get(cls, []))
                total_in += n_in
                print(f"{cls:<15} {n_in:<10} {n_out:<10}")
            
            print("-" * 40)
            print(f"TOTAL ENTERED: {total_in}")

        elapsed = datetime.now() - self.session_start_time
        print(f"\nDuration: {str(elapsed).split('.')[0]}")
        print(f"Log file: {self.json_file}")
        print("="*60 + "\n")


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    # Chạy thử với video index 0
    analyzer = AnalyzeOnRoadBase(
        video_index=0,
        show=True,
        auto_save=True,
        save_interval_seconds=60
    )
    analyzer.process_video()