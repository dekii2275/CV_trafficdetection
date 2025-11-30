# Traffic AI Dashboard – Frontend

Giao diện giám sát giao thông thời gian thực, xây dựng bằng **Next.js 14**, **TailwindCSS** và **WebSocket**.
Hệ thống hiển thị video trực tiếp, thống kê thời gian thực và các biểu đồ lịch sử lấy từ backend.

---

## Công nghệ sử dụng

* Next.js 14 (App Router)
* React 18
* TailwindCSS
* WebSocket (Realtime video frames, realtime stats)
* Recharts và SVG cho biểu đồ
* Lucide React Icons

---

## Yêu cầu hệ thống

* Node.js ≥ 18
* npm hoặc pnpm
* Backend chạy tại `localhost:8000`, gồm:

  * FastAPI (Uvicorn)
  * WebSocket endpoints
  * API thống kê lịch sử

---

## Hướng dẫn cài đặt

### Cài đặt thư viện

```bash
cd frontend
npm install
```

### Tạo file môi trường `.env.local`

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Chạy chế độ phát triển

```bash
npm run dev
```

Trình duyệt chạy tại:

```
http://localhost:3000
```

---

## Cấu trúc thư mục

```
frontend/
│
├── app/
│   ├── api/
│   │   ├── stream/         → Gateway WebSocket (proxy)
│   │   └── upload/         → Upload file từ FE
│   │
│   ├── components/
│   │   ├── charts/         → Biểu đồ (line, area, hist, boxplot…)
│   │   ├── chatbot/        → ChatBubble, giao diện chat
│   │   ├── dashboard/      → Các khối giao diện tổng hợp
│   │   ├── sidebar/        → Sidebar hệ thống
│   │   ├── stats/          → Thống kê realtime
│   │   └── stream/         → VideoPlayer, MultiCameraGrid
│   │
│   ├── layout.tsx          → Layout chung
│   └── page.tsx            → Trang dashboard chính
│
├── lib/                    → Hàm utils
├── styles/                 → Global CSS (Tailwind)
├── public/                 → Asset tĩnh
│
├── package.json
├── package-lock.json
└── README.md
```

---

## Kết nối WebSocket và API

### Video WebSocket stream

```
ws://localhost:8000/api/v1/ws/frames/{camera_id}
```

Backend gửi frame JPEG dạng **binary**.

### WebSocket thống kê realtime

```
ws://localhost:8000/api/v1/ws/info/{camera_id}
```

Trả về số lượng phương tiện theo thời gian thực.

### API biểu đồ lịch sử

| Đường dẫn                              | Mục đích             |
| -------------------------------------- | -------------------- |
| `/api/v1/charts/time-series/{cam}`     | Biểu đồ line 60 phút |
| `/api/v1/charts/stacked-area/{cam}`    | Area stacking        |
| `/api/v1/charts/grouped-bar/{cam}`     | Grouped bar          |
| `/api/v1/charts/rolling-avg/{cam}`     | Rolling average      |
| `/api/v1/charts/hist-total/{cam}`      | Histogram tổng       |
| `/api/v1/charts/boxplot/{cam}`         | Boxplot              |
| `/api/v1/charts/stacked-bar-pct/{cam}` | Bar dạng phần trăm   |

---

## Mô tả các module chính

### VideoPlayer (app/components/stream/VideoPlayer.tsx)

* Kết nối WebSocket
* Nhận khung hình dạng Blob
* Tạo blob URL và hiển thị lên `<img>`
* Tự động reconnect khi mất kết nối
* Trạng thái: đang kết nối, lỗi, online

### RealtimeStats

* Kết nối WebSocket `/ws/info/{camera_id}`
* Hiển thị số lượng phương tiện theo từng loại
* Đồng bộ realtime với backend

### Biểu đồ

Sử dụng Recharts hoặc SVG riêng:

* VehicleLineChart
* VehicleDistributionChart
* AreaChart
* GroupedBarChart
* RollingAvgChart
* HistTotalChart
* BoxplotChart
* PeaksChart

Dữ liệu được cung cấp từ API backend.

### Sidebar

* Cấu hình AI engine (model, device, precision)
* Tham số detect (Conf, IoU, frame skip)
* Các lớp phương tiện đang dùng
* Trạng thái ROI

### ChatBubble

* Giao diện chatbot
* Gửi câu hỏi về backend RAG
* Hiển thị nguồn tham khảo (ảnh hoặc văn bản)

---

## Build và triển khai

### Build production

```bash
npm run build
npm start
```

### Deploy

* Vercel (cần proxy WebSocket)
* Docker
* Nginx reverse proxy cho HTTP + WS
---