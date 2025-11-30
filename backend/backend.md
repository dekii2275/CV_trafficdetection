# Traffic AI API Docs

Backend: FastAPI 

---

## 0. Lifecycle & Background

### Khởi động hệ thống (startup event)

Khi app FastAPI start, `startup_event()` sẽ:

- Tạo `multiprocessing.Manager`, `info_dict`, `frame_dict`, `result_queue`.
- Khởi động `num_cameras = 2` process `run_analyzer(...)`.
- Tạo background task `save_stats_to_db_worker()` để 10s/lần:
  - Lấy snapshot từ `info_dict`
  - Ghi log vào bảng `TrafficLog`.

Khi tắt server, `shutdown_event()` sẽ terminate toàn bộ process.

---

## 1. Realtime Info & Frame

### 1.1. `GET /info/{camera_id}`

**Mục đích:** 
Lấy thông tin realtime (thống kê đếm xe, fps, v.v.) đang nằm trong RAM (shared dict).

**Path params:**

- `camera_id` (int) – ID camera (0, 1, ...)

**Response:**

- `200 OK` – Khi đã có data trong `sys_state.info_dict["camera_{camera_id}"]` 

  Ví dụ:

  ```json
  {
    "total_entered": 120,
    "fps": 29.7,
    "details": {
      "car":   { "entered": 80 },
      "motor": { "entered": 35 },
      "bus":   { "entered": 3 },
      "truck": { "entered": 2 }
    },
    "timestamp": 1732950000
  }
  ```

- `404 Not Found` – Khi chưa có dữ liệu:

  ```json
  { "status": "waiting" }
  ```

- `500 Internal Server Error` – Nếu hệ thống chưa init `sys_state.info_dict`.

---


### 1.2. `GET /frames/{camera_id}`

**Mục đích:** 
Lấy snapshot ảnh hiện tại của camera, để render lên UI (thumbnail / khung realtime).

**Path params:**

- `camera_id` (int)

**Response:**

- `200 OK` – Trả về bytes ảnh JPEG:

  - `Content-Type: image/jpeg`
  - Body là binary image (`frame_dict["camera_{camera_id}"]`).

- `404 Not Found` – Không có frame:

  ```json
  { "error": "No frame" }
  ```

---

## 2. Chart APIs (HTTP)

Toàn bộ chart đều dùng múi giờ **Asia/Bangkok (UTC+7)**. 
Dữ liệu được đọc từ bảng `TrafficLog` qua helper `load_traffic_df(...)`.

---

### 2.1. `GET /charts/vehicle-distribution`

**Mục đích:** 
Pie chart – phân bố loại xe trong ngày hôm nay, tính từ bản ghi mới nhất mỗi camera.

**Query params:** 
Không có.

**Response:**

```json
{
  "date": "2025-11-30",
  "totals": {
    "car": 100,
    "motor": 300,
    "bus": 10,
    "truck": 20,
    "total_vehicles": 430
  },
  "percentages": {
    "car": 0.2325,
    "motor": 0.6977,
    "bus": 0.0233,
    "truck": 0.0465
  }
}
```

---

### 2.2. `GET /charts/time-series/{camera_id}`

**Mục đích:** 
Time-series tổng số xe / phút (không cộng dồn), trong `minutes` phút gần nhất.

**Path params:**

- `camera_id` (int)

**Query params:**

- `minutes` (int, default `60`) – số phút gần nhất.

**Logic:**

1. Lấy log ~24h gần nhất.
2. Resample `1min`, dùng `max(total_vehicles)` rồi `ffill`.
3. Tính `vehicles_per_min = diff(total_vehicles)` (clip âm thành 0).
4. Lấy `tail(minutes)` để trả về.

**Response:**

```json
{
  "camera_id": 0,
  "points": [
    { "label": "18:10", "value": 5 },
    { "label": "18:11", "value": 7 }
  ],
  "period": "60m",
  "timezone": "Asia/Bangkok (UTC+7)",
  "aggregation": "per_minute"
}
```

---

### 2.3. `GET /charts/grouped-bar/{camera_id}`

**Mục đích:** 
Grouped bar chart – **số xe từng loại / phút** trong `minutes` phút gần nhất.

**Path params:**

- `camera_id` (int)

**Query params:**

- `minutes` (int, default `60`)

**Response:**

```json
{
  "camera_id": 0,
  "points": [
    {
      "label": "18:10",
      "values": {
        "count_car": 5,
        "count_motor": 12,
        "count_bus": 1,
        "count_truck": 0
      }
    }
  ],
  "classes": ["count_car", "count_motor", "count_bus", "count_truck"],
  "period": "60m",
  "timezone": "Asia/Bangkok (UTC+7)"
}
```

---

### 2.4. `GET /charts/area/{camera_id}`

**Mục đích:** 
Stacked area chart – giống grouped bar nhưng render dạng vùng (area).

**Path params:**

- `camera_id` (int)

**Query params:**

- `minutes` (int, default `60`)

**Response:**

```json
{
  "camera_id": 0,
  "points": [
    {
      "label": "18:10",
      "values": {
        "count_car": 5,
        "count_motor": 12,
        "count_bus": 1,
        "count_truck": 0
      }
    }
  ],
  "classes": ["count_car", "count_motor", "count_bus", "count_truck"],
  "period": "60m",
  "timezone": "Asia/Bangkok (UTC+7)",
  "chart_type": "stacked_area"
}
```

---

### 2.5. `GET /charts/hist-total/{camera_id}`

**Mục đích:** 
Histogram – phân bố giá trị `total_vehicles` trong ~24h gần nhất.

**Path params:**

- `camera_id` (int)

**Query params:**

- `bins` (int, default `20`) – số bin của histogram.

**Response:**

```json
{
  "camera_id": 0,
  "points": [
    { "label": "10.5", "value": 3 },
    { "label": "20.5", "value": 7 }
  ],
  "bins": 20,
  "metric": "total_vehicles"
}
```

---

### 2.6. `GET /charts/boxplot/{camera_id}`

**Mục đích:** 
Boxplot data cho từng class xe, dùng để vẽ boxplot (min, Q1, median, Q3, max).

**Path params:**

- `camera_id` (int)

**Query params:** 
Không có.

**Response:**

```json
{
  "camera_id": 0,
  "items": [
    {
      "name": "count_car",
      "min": 0.0,
      "q1": 2.0,
      "median": 5.0,
      "q3": 9.0,
      "max": 20.0
    }
  ],
  "classes": ["count_car", "count_motor", "count_bus", "count_truck"]
}
```

---

### 2.7. `GET /charts/rolling-avg/{camera_id}`

**Mục đích:** 
Rolling average (mean trượt) theo từng class xe, độ dài cửa sổ `window`, tính trên `minutes` phút gần nhất.

**Path params:**

- `camera_id` (int)

**Query params:**

- `minutes` (int, default `60`)
- `window` (int, default `5`) – rolling window size.

**Response:**

```json
{
  "camera_id": 0,
  "points": [
    {
      "label": "18:10",
      "values": {
        "count_car": 5.2,
        "count_motor": 10.7,
        "count_bus": 0.4,
        "count_truck": 0.1
      }
    }
  ],
  "classes": ["count_car", "count_motor", "count_bus", "count_truck"],
  "window": 5,
  "period": "60m",
  "timezone": "Asia/Bangkok (UTC+7)"
}
```

---

### 2.8. `GET /charts/peaks/{camera_id}`

**Mục đích:** 
Phát hiện **điểm đỉnh (peak)** của `total_vehicles` theo phút – dùng để highlight các khung giờ cao điểm.

**Path params:**

- `camera_id` (int)

**Query params:**

- `minutes` (int, default `60`)

**Logic:**

- Nếu DB đã có cột `is_peak_auto` thì sử dụng.
- Nếu chưa: tự tính `is_peak_auto = total >= quantile(0.9)`.

**Response:**

```json
{
  "camera_id": 0,
  "points": [
    {
      "label": "18:10",
      "value": 35,
      "is_peak": false,
      "timestamp": "2025-11-30T18:10:00+07:00"
    },
    {
      "label": "18:20",
      "value": 80,
      "is_peak": true,
      "timestamp": "2025-11-30T18:20:00+07:00"
    }
  ],
  "peaks": [
    {
      "label": "18:20",
      "value": 80,
      "timestamp": "2025-11-30T18:20:00+07:00"
    }
  ],
  "period": "60m",
  "timezone": "Asia/Bangkok (UTC+7)"
}
```

---

## 3. WebSocket APIs

### 3.1. `WS /ws/frames/{camera_id}`

**Mục đích:** 
Stream các frame JPEG (bytes) của camera theo thời gian thực.

**Path params:**

- `camera_id` (int)

**Protocol:**

- Server:
  - `await websocket.accept()`
  - Vòng lặp:
    - Lấy frame từ `frame_dict["camera_{camera_id}"]`
    - Nếu khác frame cũ → `await websocket.send_bytes(frame_bytes)`
    - `await asyncio.sleep(0.05)`

- Client (pseudo-code):

  ```js
  const ws = new WebSocket("ws://server/ws/frames/0");
  ws.binaryType = "blob";

  ws.onmessage = (event) => {
    const url = URL.createObjectURL(event.data);
    imgElement.src = url;
  };
  ```

---

### 3.2. `WS /ws/info/{camera_id}`

**Mục đích:** 
Stream JSON realtime info (thống kê, fps, v.v.) cho frontend dashboard.

**Path params:**

- `camera_id` (int)

**Protocol:**

- Server:
  - `await websocket.accept()`
  - Vòng lặp:
    - Lấy `sys_state.info_dict["camera_{camera_id}"]`
    - Nếu `timestamp` (hoặc content) thay đổi:
      - `await websocket.send_json(current_data)`
    - `await asyncio.sleep(0.5)`

- Client (pseudo-code):

  ```js
  const ws = new WebSocket("ws://server/ws/info/0");

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // update UI
  };
  ```

---


## 4. Chat Message History APIs

Các API này quản lý lịch sử chat trong DB: lưu tin nhắn, list history theo session, thống kê, dọn rác, v.v.

Base prefix gợi ý: `/api/v1/chat-history` (tùy bạn mount router).

---

### 4.1. `POST /messages`

**Mục đích:** 
Lưu một tin nhắn chat (của user hoặc bot) vào DB, có **session tracking**.

**Body (JSON, `ChatMessageCreate` – mô tả theo code):**

```json
{
  "message": "Xin chào",
  "is_user": true,
  "images": [],
  "extra_data": {},
  "session_id": "optional-session-id"
}
```

- `message` *(string, required)* – nội dung tin nhắn.
- `is_user` *(bool, required)* – `true` nếu là tin nhắn của user, `false` nếu là bot.
- `images` *(list, optional)* – các thông tin ảnh đính kèm.
- `extra_data` *(object, optional)* – metadata thêm (token, debug, v.v.).
- `session_id` *(string, optional)* – nếu không truyền, server **tự tạo** một `uuid`.

**Response `201 Created` (`ChatMessageResponse`):**

Trả về bản ghi vừa lưu, ví dụ:

```json
{
  "id": 123,
  "message": "Xin chào",
  "is_user": true,
  "images": [],
  "extra_data": {},
  "session_id": "f8e9c7c2-....",
  "created_at": "2025-11-30T18:10:00Z"
}
```

---

### 4.2. `GET /messages`

**Mục đích:** 
Lấy lịch sử chat, có thể lọc theo `session_id`.

**Query params:**

- `session_id` *(string, optional)* – nếu có, chỉ lấy tin nhắn thuộc session này.
- `limit` *(int, default `100`, 1–1000)* – số bản ghi tối đa.
- `offset` *(int, default `0`)* – bỏ qua N bản ghi đầu (paging).
- `since` *(datetime ISO, optional)* – chỉ lấy các tin nhắn **sau thời điểm này**.

**Response `200 OK` (mảng `ChatMessageListResponse`):**

```json
[
  {
    "id": "123",
    "text": "Xin chào",
    "user": true,
    "time": "18:10:00",
    "image": [],
    "created_at": "2025-11-30T18:10:00Z",
    "session_id": "f8e9c7c2-...."
  }
]
```

---

### 4.3. `GET /messages/context/{session_id}`

**Mục đích:** 
Lấy **N tin nhắn gần nhất** của một session để làm **context cho RAG / LLM**.

**Path params:**

- `session_id` *(string)* – id phiên chat.

**Query params:**

- `last_n` *(int, default `10`, 1–50)* – số tin nhắn gần nhất.

**Response `200 OK`:**

```json
{
  "session_id": "f8e9c7c2-....",
  "message_count": 4,
  "context": [
    {
      "role": "user",
      "content": "Xin chào",
      "timestamp": "2025-11-30T18:10:00Z"
    },
    {
      "role": "assistant",
      "content": "Chào bạn, mình có thể giúp gì?",
      "timestamp": "2025-11-30T18:10:05Z"
    }
  ]
}
```

> `role` được map từ cột `is_user`: `true → "user"`, `false → "assistant"`.

---

### 4.4. `GET /sessions`

**Mục đích:** 
Liệt kê tất cả các **session** cùng metadata cơ bản.

**Query params:**

- `active_only` *(bool, default `false`)* – nếu `true`, chỉ lấy những session có hoạt động trong **24h gần nhất**.

**Response `200 OK`:**

```json
{
  "total_sessions": 2,
  "sessions": [
    {
      "session_id": "f8e9c7c2-....",
      "first_message_at": "2025-11-30T17:00:00Z",
      "last_message_at": "2025-11-30T18:10:00Z",
      "message_count": 25,
      "duration_minutes": 70
    }
  ]
}
```

- `duration_minutes` = `last_message_at - first_message_at` (tính bằng phút).

---

### 4.5. `DELETE /sessions/{session_id}`

**Mục đích:** 
Xóa **toàn bộ lịch sử** của một session (user muốn xóa conversation).

**Path params:**

- `session_id` *(string)* – id phiên chat.

**Response:**

- `204 No Content` – xóa thành công.
- `404 Not Found` – nếu không tồn tại session.

---

### 4.6. `DELETE /sessions/cleanup`

**Mục đích:** 
Dọn dẹp **các session cũ** không hoạt động quá X ngày.

**Query params:**

- `days` *(int, default `30`, 1–365)* – xóa các session mà **tin nhắn cuối cùng** của chúng cũ hơn `days` ngày.

**Response `200 OK`:**

```json
{
  "deleted_sessions": 3,
  "deleted_messages": 120,
  "cutoff_date": "2025-10-31T00:00:00Z"
}
```

Nếu không có session nào quá cũ:

```json
{
  "deleted_sessions": 0,
  "message": "No old sessions to delete"
}
```

---

### 4.7. `GET /statistics`

**Mục đích:** 
Thống kê tổng quan về việc sử dụng chatbot (usage dashboard).

**Response `200 OK`:**

```json
{
  "total_messages": 1200,
  "total_sessions": 80,
  "messages_last_24h": 150,
  "avg_messages_per_session": 15.0,
  "generated_at": "2025-11-30T18:12:00Z"
}
```

---

### 4.8. `DELETE /messages/{message_id}`

**Mục đích:** 
Xóa **một** tin nhắn cụ thể.

**Path params:**

- `message_id` *(int)* – ID của tin nhắn trong DB.

**Response:**

- `204 No Content` – xóa thành công.
- `404 Not Found` – không tìm thấy message.

---

## 5. Chatbot / RAG APIs

Các API này là “lớp trên” của chat-history: thực sự chat với AI (RAG), đồng thời **lưu lại** lịch sử vào bảng `ChatMessage`.

Base prefix gợi ý: `/api/v1/chatbot`.

---

### 5.1. Startup – khởi tạo RAG Agent

```py
@router.on_event("startup")
async def start_up():
    \"\"\"Khởi tạo RAG Chat Agent\"\"\"
    ...
```

Khi service khởi động, nó:

- Gọi `get_agent()` để init RAG agent.
- In ra log: tổng số document, trạng thái vector DB, v.v.

---

### 5.2. `POST /chat`

**Mục đích:** 
Chat 1 turn với AI (RAG), có **lưu lại** cả câu hỏi & câu trả lời vào DB.

**Body (JSON – `ChatRequest`):**

Ví dụ (suy ra từ code):

```json
{
  "message": "Hãy tư vấn giúp tôi...",
  "session_id": "optional-session-id"
}
```

- `message` *(string, required)* – câu hỏi của user.
- `session_id` *(string, optional)*:
  - Nếu **có**: dùng tiếp session cũ → giữ ngữ cảnh.
  - Nếu **không**: server tự tạo `uuid` mới cho phiên chat.

**Logic server (tóm tắt):**

1. Lấy / tạo `session_id`.
2. `save_to_db(session_id, "user", request.message)` – lưu câu hỏi vào DB.
3. `get_db_history(session_id)` – lấy ~10 tin nhắn gần nhất làm **conversation history**.
4. Gọi `agent.get_response(message, session_id, conversation_history)`.
5. Lưu câu trả lời AI vào DB: `save_to_db(session_id, "assistant", response["message"], sources, images)`.
6. Trả về `ChatResponse`.

**Response `200 OK` (`ChatResponse`):**

```json
{
  "message": "Đây là câu trả lời từ AI...",
  "image": [],
  "session_id": "f8e9c7c2-....",
  "sources": []
}
```

> `image` & `sources` có thể là mảng rỗng nếu agent không sinh thêm gì.

---

### 5.3. `WS /ws/chat` – WebSocket Chat

**Mục đích:** 
Chat realtime qua WebSocket, **tự tạo session mới** cho mỗi kết nối, và vẫn lưu vào DB.

**Cách hoạt động:**

- Khi client connect:
  - Server `accept()` và tạo `session_id = uuid4()`.
  - Gửi lại cho client gói:

    ```json
    {
      "type": "session_init",
      "session_id": "f8e9c7c2-...."
    }
    ```

- Sau đó, vòng lặp:

  1. Client gửi:

     ```json
     {
       "message": "Câu hỏi của user..."
     }
     ```

  2. Server:
     - `save_to_db(session_id, "user", user_message)`.
     - Lấy history: `conversation_history = get_db_history(session_id)`.
     - Gửi trạng thái tạm:

       ```json
       {
         "type": "status",
         "message": " Đang tra cứu..."
       }
       ```

     - Gọi `agent.get_response(...)`.
     - Lưu câu trả lời AI vào DB.
     - Gửi lại client:

       ```json
       {
         "type": "complete",
         "message": "Câu trả lời của AI...",
         "image": [],
         "sources": []
       }
       ```

  3. Nếu có lỗi trong xử lý:

     ```json
     {
       "type": "error",
       "message": "Mô tả lỗi..."
     }
     ```

- Khi client đóng kết nối → `WebSocketDisconnect` → log `"WS Disconnected: {session_id}"`.

**Client pseudo-code (JS):**

```js
const ws = new WebSocket("ws://server/api/v1/chatbot/ws/chat");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "session_init") {
    sessionId = data.session_id;
  } else if (data.type === "status") {
    // show loading / status text
  } else if (data.type === "complete") {
    // render AI answer + data.image + data.sources
  } else if (data.type === "error") {
    // show error
  }
};

function sendMessage(text) {
  ws.send(JSON.stringify({ message: text }));
}
```

---

### 5.4. `DELETE /chat/session/{session_id}`

**Mục đích:** 
Xóa toàn bộ lịch sử chat của một `session_id` trong DB (cho chatbot RAG này). 
Khá giống `DELETE /sessions/{session_id}` bên chat-history, nhưng được đặt tại router chatbot.

**Path params:**

- `session_id` *(string)* – id phiên chat.

**Response:**

- `200 OK`:

  ```json
  { "message": "Đã xóa lịch sử chat trong DB" }
  ```

- `500 Internal Server Error` – nếu có lỗi DB.

---

## 6. Tóm tắt Mapping Chatbot ↔ History

- **Ghi / Đọc lịch sử chi tiết:**
  - `POST /messages`, `GET /messages`, `GET /messages/context/{session_id}`, …
- **Quản lý sessions & thống kê:**
  - `GET /sessions`, `DELETE /sessions/{session_id}`, `DELETE /sessions/cleanup`, `GET /statistics`.
- **Layer Chatbot (RAG):**
  - `POST /chat` – chat HTTP 1 turn.
  - `WS /ws/chat` – chat streaming qua WebSocket.
  - `DELETE /chat/session/{session_id}` – xóa conversation cho chatbot UI.
