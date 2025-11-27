import os
import cv2
import numpy as np
from multiprocessing import Process, Manager
from app.services.road_services.AnalyzeOnRoadBase import AnalyzeOnRoadBase
from app.core.config import settings_metric_transport

# Fix lỗi duplicate libomp trên Mac/Linux
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class AnalyzeOnRoad(AnalyzeOnRoadBase):
    """
    Class kế thừa từ AnalyzeOnRoadBase (đã fix logic ROI).
    Nhiệm vụ:
    - Chạy logic đếm xe của lớp cha.
    - Đẩy kết quả (số lượng xe, hình ảnh đã vẽ) ra ngoài qua Manager.dict
    - Để phục vụ Multiprocessing hoặc API Streaming.
    """

    def __init__(
        self,
        video_index: int,       # Index trong config (0 hoặc 1...)
        info_dict: dict,        # Shared dict để lưu số liệu đếm
        frame_dict: dict,       # Shared dict để lưu frame ảnh (bytecode)
        show: bool = True
    ):
        """
        Args:
            video_index: Số thứ tự video trong settings_metric_transport
            info_dict: Dictionary chia sẻ (Multiprocessing Manager)
            frame_dict: Dictionary chia sẻ frame ảnh
            show: Có hiển thị cửa sổ OpenCV không
        """
        # 1. Gọi Init lớp cha
        # Lớp cha sẽ tự load path_video, model, và ROI dựa trên video_index
        super().__init__(video_index=video_index, show=show)

        # 2. Lưu biến riêng của lớp con
        self.info_dict = info_dict
        self.frame_dict = frame_dict
        self.processes = []  # Quản lý process con nếu cần mở rộng sau này

    def process_single_frame(self, frame):
        """
        GHI ĐÈ (Override) hàm xử lý frame của lớp cha.
        Mục đích:
        1. Gọi logic đếm xe của lớp cha (super).
        2. Sau khi có kết quả, cập nhật vào info_dict và frame_dict.
        """
        
        # --- BƯỚC 1: Gọi logic cốt lõi của lớp cha ---
        # Hàm này sẽ update self.counted_ids và trả về ảnh đã vẽ (plotted)
        plotted_frame = super().process_single_frame(frame)

        # --- BƯỚC 2: Đồng bộ dữ liệu ra bên ngoài (cho API/Process khác) ---
        self._update_shared_data(plotted_frame)

        return plotted_frame

    def _update_shared_data(self, frame):
        """Cập nhật dữ liệu vào Manager Dict"""
        try:
            # 1. Cập nhật số liệu đếm xe
            # self.counted_ids là dict { "car": {id1, id2}, "bus": {id3} }
            
            count_summary = {}
            total_all = 0
            
            if self.counted_ids:
                for cls_name, id_set in self.counted_ids.items():
                    count = len(id_set)
                    count_summary[f"count_{cls_name}"] = count
                    total_all += count
            
            # Ghi vào info_dict (dùng key chuẩn để frontend dễ lấy)
            self.info_dict["details"] = count_summary
            self.info_dict["total"] = total_all
            
            # Nếu cần tương thích code cũ (count_car, count_motor)
            self.info_dict["count_car"] = len(self.counted_ids.get("car", []))
            self.info_dict["count_motor"] = len(self.counted_ids.get("motorcycle", [])) + len(self.counted_ids.get("motorbike", []))

            # 2. Cập nhật Frame ảnh (Encode sang JPEG để nhẹ băng thông)
            if self.frame_dict is not None:
                _, buffer = cv2.imencode('.jpg', frame)
                self.frame_dict["frame_bytes"] = buffer.tobytes()

        except Exception as e:
            # Không print lỗi liên tục để tránh spam log
            pass

    def cleanup_processes(self):
        """Dọn dẹp (nếu có spawn thêm process con)"""
        print(f"🛑 Cleaning up analyzer for video {self.path_video}...")
        # Hiện tại class này chạy trực tiếp trên process chính nên không có gì để kill
        # Nhưng giữ hàm này để tương thích interface cũ
        pass


# ============================================================
# SCRIPT TEST (Chạy độc lập)
# ============================================================
if __name__ == "__main__":
    from multiprocessing import Manager

    # 1. Giả lập môi trường Multiprocessing
    manager = Manager()
    
    # Dict dùng chung
    shared_info = manager.dict()
    shared_frame = manager.dict()

    # 2. Khởi tạo Analyzer (Lớp con)
    # Lưu ý: Class cha tự lấy config dựa trên index=0 (video đầu tiên)
    print("🚀 Khởi tạo Analyzer...")
    
    analyzer = AnalyzeOnRoad(
        video_index=0, 
        info_dict=shared_info,
        frame_dict=shared_frame,
        show=True
    )
    
    # 3. Chạy loop (Process chính)
    try:
        # Hàm này của lớp cha, nó sẽ gọi process_single_frame của con
        analyzer.process_video()
    except KeyboardInterrupt:
        print("\n🛑 Dừng chương trình thủ công.")
    except Exception as e:
        print(f"❌ Lỗi Runtime: {e}")
    finally:
        analyzer.cleanup_processes()