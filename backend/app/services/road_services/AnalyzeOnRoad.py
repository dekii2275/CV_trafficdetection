from datetime import datetime
import traceback
# Import class từ file Base vừa tạo ở trên
from app.services.road_services.AnalyzeOnRoadBase import AnalyzeOnRoadBase

# ============================================================
# RUN FUNCTION (Được gọi bởi Process trong api_vehicles.py)
# ============================================================

def run_analyzer(video_index, shared_dict, result_queue, frame_dict=None, show_window=False):
    """
    Wrapper function để chạy Analyzer trong Process riêng biệt.
    
    Args:
        video_index (int): ID của camera
        shared_dict (Manager.dict): Để lưu thông số đếm (số lượng xe, fps...)
        result_queue (Queue): Để báo trạng thái (start/error)
        frame_dict (Manager.dict): Để lưu hình ảnh realtime (byte jpg)
        show_window (bool): Có hiện cửa sổ CV2 không (thường là False trên server)
    """
    try:
        # Khởi tạo Analyzer
        analyzer = AnalyzeOnRoadBase(
            video_index=video_index,
            shared_dict=shared_dict,
            result_queue=result_queue,
            frame_dict=frame_dict,  # <--- Đã truyền đúng tham số này
            show=show_window,
            auto_save=True,
            save_interval_seconds=60
        )
        
        # Bắt đầu vòng lặp xử lý video
        analyzer.process_video()
        
        # Gửi tín hiệu hoàn thành khi vòng lặp kết thúc
        if result_queue:
            result_queue.put({
                'camera': video_index,
                'status': 'completed',
                'timestamp': datetime.now().timestamp()
            })
        
    except Exception as e:
        print(f"[Camera {video_index}] 💥 CRASH: {e}")
        traceback.print_exc()
        if result_queue:
            result_queue.put({
                'camera': video_index,
                'status': 'error',
                'error': str(e)
            })