"""
Global State Management
Lưu trữ trạng thái chia sẻ giữa các luồng/tiến trình (nếu cần).
Trong kiến trúc Multiprocessing mới, dữ liệu chính nằm trong Manager.dict() 
được quản lý bên api_vehicles.py, nhưng file này vẫn cần tồn tại để tránh lỗi import.
"""

# Các biến global giữ chỗ (Placeholders)
# Hệ thống cũ dùng 'analyzer', hệ thống mới dùng 'processes' và 'manager'
analyzer = None 
manager = None
info_dict = None
frame_dict = None
processes = []