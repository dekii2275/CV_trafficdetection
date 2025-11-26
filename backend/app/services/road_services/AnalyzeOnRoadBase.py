import os
from abc import abstractmethod
import cvzone
import cv2
import numpy as np
from datetime import datetime
from ultralytics import solutions
from app.utils.transport_utils import avg_none_zero_batch
from app.core.config import settings_metric_transport
from cap_from_youtube import cap_from_youtube
import yt_dlp

# Thêm cái này để tránh xung đột
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def get_stream_url(youtube_url):
    """
    Lấy direct stream URL chất lượng 'best' từ YouTube bằng yt_dlp.
    Không fallback.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best", 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            url = info.get("url", None)

            if url:
                print("Lấy stream thành công ở chất lượng: best")
                return url

    except Exception as e:
        print(f"Không lấy được stream YouTube: {e}")

    print("Không lấy được stream 'best'!")
    return None



class AnalyzeOnRoadBase:
    """Class gói gọn script xử lý tuần tự nhưng đảm bảo tính đóng gói OOP
        Attributes:
            count_car_display (int): số lượng xe oto trung bình
            speed_car_display (int): trung bình tốc độ tức thời của oto
            count_moto_display (int): số lượng xe xe máy trung bình
            speed_moto_display (int): trung bình tốc độ tức thời của xe máy
            speed_tool (solutions.SpeedEstimator()): đối tượng SpeedEstimator của YOLO
            frame_output (np.array): ảnh đã qua xử lý được vẽ hoặc không vẽ (tuỳ vào biến is_draw)\
            các thông tin được chuẩn đoán
        Examples:
            Hướng dẫn chạy xử lý 1 video đơn
            >>> analyzer = AnalyzeOnRoadBase(
            >>>     path_video=path_video,
            >>>     meter_per_pixel=meter_per_pixel,
            >>>     info_dict=info_dict,
            >>>     frame_dict=frame_dict,
            >>>     lock_info=lock_info,
            >>>     lock_frame=lock_frame,
            >>> )
            >>> analyzer.process_on_single_video()
    """
    def __init__(self, path_video, meter_per_pixel = 0.06,
                 model_path= settings_metric_transport.MODELS_PATH, time_step=30,
                 is_draw=True, device= settings_metric_transport.DEVICE, iou=0.3, conf=0.2, show=False,
                 region = np.array([[50, 400], [50, 265], [370, 130], [600, 130], [600, 400]])):
        """Hàm xử lý tuần tự như một Script đơn giản áp dụng YOLO và cải tiến hơn là ở việc gói gọn trong 1 class

        Args:
            path_video (str): Đường dẫn đến video
            meter_per_pixel (float): Tỉ lệ 1 mét ngoài đời với 1 pixel
            model_path (str): Đường dẫn đến model. Defaults to "best.pt".
            time_step (int): Khoảng thời gian giữa 2 lần cập nhật thông tin các phương tiện. Defaults to 30.
            is_draw (bool): Biến chỉ định có vẽ các thông tin xử lý được lên frame hay không. Defaults to True.
            device (str): Dùng GPU hoặc CPU. Defaults to 'cpu'.
            iou (float): Ngưỡng tin cậy về bounding box . Defaults to 0.3.
            conf (float): Ngưỡng tin cậy về nhãn được dự đoán. Defaults to 0.2.
            show (bool): Hiển thị video xử lý qua opencv, đặt là False khi tích hợp làm server tránh lãng phí tài nguyên.\
            Defaults to True.
            max_buffer_size (int): Kích thước tối đa của buffer cho deque. Defaults to 900.
        """
        self.speed_tool = solutions.SpeedEstimator(
            model=model_path,
            tracker = 'bytetrack.yaml',
            verbose=False,
            show=False,
            device=device,
            iou=iou,
            conf=conf,
            meter_per_pixel=meter_per_pixel,
            max_hist=20
        )

        self.region = region
        self.region_pts = region.reshape((-1, 1, 2))
        # Bounding box (x, y, w, h) for fast pre-filtering before polygon test
        self.region_bbox = cv2.boundingRect(self.region_pts)

        self.show = show
        self.path_video = path_video
        self.name = "Youtube_Stream" if "http" in path_video else path_video.split('/')[-1][:-4]

        self.count_car_display = 0
        self.list_count_car = []
        self.speed_car_display = 0
        self.list_speed_car = []

        self.count_motor_display = 0
        self.list_count_motor = []
        self.speed_motor_display = 0
        self.list_speed_motor = []

        self.time_pre = datetime.now()
        self.frame_output = None
        self.time_step = time_step
        self.frame_predict = None
        self.is_draw = is_draw
        self.delta_time = 0
        self.time_pre_for_fps = datetime.now()

        # ROI
        self.roi_y_start = 0
        self.roi_x_start = 0

        # Draw
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.5
        self.font_thickness = 1
        self.color_motor = (0, 0, 255)  # Red for motorcycles
        self.color_car = (255, 0, 0)    # Blue for cars
        self.color_region = (0, 255, 255)  # Yellow for region

        # Tracking
        self.ids = None
        self.speeds = {}
        self.boxes = None
        self.classes = None
        self.ids_old = set()
    @abstractmethod
    def update_for_frame(self):
        pass

    @abstractmethod
    def update_for_vehicle(self):
        pass

    def update_data(self):
        """Hàm này sẽ được gọi để cập nhật dữ liệu cho frame và thông tin phương tiện sau một khoảng thời gian
            đã thiết lập là time_step"""

        # Gọi hàm này để cập nhật dữ liệu cho frame (luôn được cập nhật đảm bảo tính realtime)
        self.update_for_frame()

        # Tính toán thời gian đã trôi qua kể từ lần cập nhật trước
        time_now = datetime.now()
        self.delta_time = (time_now - self.time_pre).total_seconds()

        # Khi đủ thời gian đã thiết lập, cập nhật thông tin phương tiện
        if self.delta_time >= self.time_step:
            self.time_pre = time_now

            # Tính toán trung bình các giá trị theo chu kỳ (bỏ qua 0)
            (
                self.count_car_display,
                self.speed_car_display,
                self.count_motor_display,
                self.speed_motor_display,
            ) = avg_none_zero_batch(
                self.list_count_car,
                self.list_speed_car,
                self.list_count_motor,
                self.list_speed_motor,
            )

            # Cập nhật thông tin phương tiện vào info_dict
            self.update_for_vehicle()

            # Reset danh sách để chuẩn bị cho lần cập nhật tiếp theo
            self.list_count_car.clear()
            self.list_count_motor.clear()
            self.list_speed_car.clear()
            self.list_speed_motor.clear()
            self.ids_old.clear()

    def process_single_frame(self, frame_input):
        """Hàm này xử lý từng frame một
        Args:
            frame_input (np.array): Ảnh được đọc từ opencv
        """
        try:
            # Tránh copy toàn bộ frame, chỉ tạo view
            self.frame_output = frame_input

            # Sử dụng view trực tiếp ROI (tránh copy thừa); copy sẽ được thực hiện khi đưa vào speed_tool
            self.frame_predict = self.frame_output[self.roi_y_start:, self.roi_x_start:]

            # Cần dùng bản copy để tránh công cụ ghi đè label lên ảnh đầu vào
            self.speed_tool.process(self.frame_predict.copy())

            self.post_processing()

            # Vẽ đè lên hình các thông tin
            if self.is_draw:
                self.draw_info_to_frame_output()
            # p = Thread(target= lambda : self.post_processing())
            # p.start()


            # Cập nhật data
            self.update_data()

        except Exception as e:
            print(f"Lỗi khi xử lý với file {self.name}: {e}")

    def post_processing(self):
        if self.speed_tool.track_data is not None:
            # Batch convert to numpy một lần (giảm nhiều lần truy cập thuộc tính)
            track_data = self.speed_tool.track_data
            speeds_dict = self.speed_tool.spd  # dict: id -> speed

            ids = track_data.id.cpu().numpy().astype(np.int32)
            classes = track_data.cls.cpu().numpy().astype(np.int32)
            boxes = track_data.xyxy.cpu().numpy().astype(np.int32)

            # Lưu vào thuộc tính phục vụ vẽ
            self.speeds = speeds_dict
            self.ids = ids
            self.classes = classes
            self.boxes = boxes

            # Đếm mật độ tức thời
            car_mask = (classes == 0)
            motor_mask = (classes == 1)
            self.list_count_car.append(int(np.sum(car_mask)))
            self.list_count_motor.append(int(np.sum(motor_mask)))

            car_ids = ids[car_mask]
            motor_ids = ids[motor_mask]
            ids_old = self.ids_old

            def collect_speeds(new_ids: np.ndarray):
                if new_ids.size == 0:
                    return []
                if ids_old:
                    mask_new = ~np.isin(new_ids, list(ids_old), assume_unique=False)
                    new_ids = new_ids[mask_new]
                if new_ids.size == 0:
                    return []
                spd_arr = np.array([speeds_dict.get(int(i), 0.0) for i in new_ids], dtype=np.float32)
                valid_mask = spd_arr > 0.0
                if not np.any(valid_mask):
                    return []
                ids_old.update(new_ids[valid_mask].tolist())
                return spd_arr[valid_mask].tolist()

            car_speeds = collect_speeds(car_ids)
            motor_speeds = collect_speeds(motor_ids)
            if car_speeds:
                self.list_speed_car.extend(car_speeds)
            if motor_speeds:
                self.list_speed_motor.extend(motor_speeds)


    def draw_info_to_frame_output(self):
        """Hàm này để vẽ các thông tin lên ảnh - optimized version"""
        try:
            if self.ids is not None and len(self.ids) > 0:
                # Vectorized center calculation
                x1 = self.boxes[:, 0]
                y1 = self.boxes[:, 1]
                x2 = self.boxes[:, 2]
                y2 = self.boxes[:, 3]

                cx = ((x1 + x2) // 2).astype(np.int32)
                cy = ((y1 + y2) // 2).astype(np.int32)

                # Batch ROI
                cx_adj = cx + self.roi_x_start
                cy_adj = cy + self.roi_y_start

                # Tìm các điểm nằm trong vùng ROI: prefilter bằng bounding box để giảm số lần pointPolygonTest
                bx, by, bw, bh = self.region_bbox
                in_bbox_mask = (
                    (cx_adj >= bx) & (cx_adj < bx + bw) &
                    (cy_adj >= by) & (cy_adj < by + bh)
                )
                candidate_idx = np.nonzero(in_bbox_mask)[0]
                valid_list = []
                region_pts_local = self.region_pts  # local ref
                for idx in candidate_idx:
                    if cv2.pointPolygonTest(region_pts_local, (int(cx_adj[idx]), int(cy_adj[idx])), False) >= 0:
                        valid_list.append(idx)
                if valid_list:
                    valid_indices = np.asarray(valid_list, dtype=np.int32)
                else:
                    valid_indices = np.empty((0,), dtype=np.int32)

                for idx in valid_indices:
                    track_id = self.ids[idx]
                    class_id = self.classes[idx]
                    speed_id = self.speeds.get(track_id, 0)

                    color = self.color_motor if class_id == 1 else self.color_car
                    label = f"{speed_id} km/h"

                    cx_local = cx[idx]
                    cy_local = cy[idx]

                    cv2.putText(self.frame_predict, label,
                               (cx_local - 50, cy_local - 15),
                               self.font, self.font_scale, color, self.font_thickness)
                    cv2.circle(self.frame_predict, (cx_local, cy_local), 5, color, -1)

            # Gắn lại vùng được cắt để predict lại vào frame ban đầu
            self.frame_output[self.roi_y_start:, self.roi_x_start:] = self.frame_predict
            cv2.polylines(self.frame_output, [self.region_pts],
                         isClosed=True, color=self.color_region, thickness=4)

            info = [
                f"Xe may: {self.count_motor_display} xe, Vtb = {self.speed_motor_display} km/h",
                f"Oto: {self.count_car_display} xe, Vtb = {self.speed_car_display} km/h"
            ]

            colors = [(0, 0, 200), (200, 0, 0)]

            # for i, t in enumerate(info):
            #     cvzone.putTextRect(
            #         self.frame_output, t,
            #         (10, 25 + i * 35),
            #         scale=1.5, thickness=2,
            #         colorT=colors[i],
            #         colorR=(50, 50, 50),
            #         border=2,
            #         colorB=(255, 255, 255)
            #     )

        except Exception as e:
            print(f"Lỗi khi vẽ: {e}")

    def process_on_single_video(self):
        """Xử lý livestream YouTube bằng yt_dlp."""
        
        # Lấy URL stream
        stream_url = get_stream_url(self.path_video)

        if stream_url is None:
            print("Không thể lấy stream YouTube. Dừng lại.")
            return

        cam = cv2.VideoCapture(stream_url)

        if not cam.isOpened():
            print(f"Không thể mở livestream: {self.path_video}")
            return

        try:
            while True:
                ok, frame = cam.read()
                if not ok:
                    print("Livestream ngắt hoặc không đọc được frame.")
                    break

                frame = cv2.resize(frame, (1280, 720))

                time_now = datetime.now()
                delta = (time_now - self.time_pre_for_fps).total_seconds()
                fps = round(1 / delta) if delta > 0 else 0
                self.time_pre_for_fps = time_now

                # Vẽ FPS
                cvzone.putTextRect(
                    frame, f"FPS: {fps}", (50, 50),
                    scale=1.1, thickness=2,
                    colorT=(0, 255, 100),
                    colorR=(50, 50, 50),
                    border=2,
                    colorB=(255, 255, 255),
                )

                self.process_single_frame(frame)

                # ====== Hiển thị ======
                if self.show:
                    cv2.imshow(f"{self.name}", self.frame_output)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

        except KeyboardInterrupt:
            print("⛔ Người dùng dừng livestream.")

        except Exception as e:
            print(f"❌ Lỗi livestream: {e}")

        finally:
            cam.release()
            if self.show:
                cv2.destroyAllWindows()




#************************** Script for testing ***************************************
if __name__ == "__main__":
    # Example usage
    path_video = settings_metric_transport.PATH_VIDEOS[0]
    meter_per_pixel = settings_metric_transport.METER_PER_PIXELS[0]
    region = settings_metric_transport.REGIONS[0]

    analyzer = AnalyzeOnRoadBase(
        path_video=path_video,
        meter_per_pixel=meter_per_pixel,
        region=region,
        show=True
    )
    
    analyzer.process_on_single_video()