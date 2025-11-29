# Hướng dẫn chạy dự án Traffic Detection

## Yêu cầu hệ thống
- Python 3.8+
- Node.js 18+
- npm hoặc yarn

## Bước 1: Cài đặt Backend

```bash
# Di chuyển vào thư mục backend
cd backend

# Tạo virtual environment (nếu chưa có)
python -m venv venv

# Kích hoạt virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Cài đặt dependencies
pip install -r ../requirements.txt
```

## Bước 2: Cài đặt Frontend

```bash
# Di chuyển vào thư mục frontend
cd frontend

# Cài đặt dependencies
npm install
```

## Bước 3: Chạy Backend

Mở terminal mới và chạy:

```bash
# Di chuyển vào thư mục backend
cd backend

# Kích hoạt virtual environment (nếu chưa kích hoạt)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Chạy server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend sẽ chạy tại: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Bước 4: Chạy Frontend

Mở terminal mới và chạy:

```bash
# Di chuyển vào thư mục frontend
cd frontend

# Chạy development server
npm run dev
```

Frontend sẽ chạy tại: `http://localhost:3000`

## Truy cập ứng dụng

Mở trình duyệt và truy cập: `http://localhost:3000`

## Lưu ý

1. **Backend cần chạy trước** để frontend có thể kết nối API
2. **Camera/Video source**: Hệ thống sẽ tự động khởi động 2 camera processes. Nếu không có camera thật, có thể cần cấu hình video source trong `configs/app.yaml`
3. **Database**: Hệ thống sử dụng SQLite mặc định, không cần cấu hình thêm
4. **Log files**: Dữ liệu thống kê được lưu trong `backend/logs/traffic_count/`

## Troubleshooting

### Lỗi import module
- Đảm bảo đã cài đặt đầy đủ dependencies từ `requirements.txt`
- Kiểm tra virtual environment đã được kích hoạt

### Lỗi kết nối API
- Kiểm tra backend đã chạy tại port 8000
- Kiểm tra CORS settings trong `backend/app/main.py`

### Lỗi camera
- Kiểm tra camera có được kết nối không
- Xem log trong terminal backend để biết chi tiết lỗi

