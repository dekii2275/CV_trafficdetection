import sys
import os
import random
from datetime import datetime, timedelta

# Setup đường dẫn để import được app
sys.path.append(os.getcwd())

from app.db.base import SessionLocal
from app.models.traffic_logs import TrafficLog

def seed_traffic_data(camera_id=0, minutes=60):
    print(f"🌱 Đang tạo dữ liệu giả cho Camera {camera_id} trong {minutes} phút qua...")
    
    db = SessionLocal()
    try:
        # Xóa dữ liệu cũ của cam này để tránh trùng lặp
        # db.query(TrafficLog).filter(TrafficLog.camera_id == camera_id).delete()
        
        now = datetime.now()
        start_time = now - timedelta(minutes=minutes)
        
        # Giả lập số xe tích lũy ban đầu
        current_total = 1000 
        
        # Tạo dữ liệu cho từng phút
        for i in range(minutes + 5): # Thêm 5 phút dư
            timestamp = start_time + timedelta(minutes=i)
            
            # Tăng ngẫu nhiên số xe (Flow rate: 5 - 30 xe/phút)
            flow = random.randint(5, 30)
            
            # Giả lập cao điểm (phút thứ 30-45)
            if 30 < i < 45: 
                flow += random.randint(20, 40)
            
            current_total += flow
            
            # Chia tỉ lệ ngẫu nhiên
            car = int(current_total * 0.6)
            motor = int(current_total * 0.3)
            truck = int(current_total * 0.05)
            bus = current_total - car - motor - truck
            
            log = TrafficLog(
                camera_id=camera_id,
                timestamp=timestamp,
                total_vehicles=current_total,
                count_car=car,
                count_motor=motor,
                count_truck=truck,
                count_bus=bus,
                fps=25.5
            )
            db.add(log)
            
        db.commit()
        print(f"✅ Đã thêm {minutes + 5} bản ghi cho Camera {camera_id}")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Tạo dữ liệu cho cả 2 cam
    seed_traffic_data(camera_id=0)
    seed_traffic_data(camera_id=1)
    print("🎉 Hoàn tất! Hãy F5 lại trang Dashboard.")