# 🤖 Báo cáo Bài tập nhóm Môn Trí tuệ Nhân tạo

**📋 Thông tin:**

[Các thông tin này cũng cần được đưa vào báo cáo PDF và slide trình bày.]

* **📚 Môn học:** MAT3508 - Nhập môn Trí tuệ Nhân tạo  
* **📅 Học kỳ:** Học kỳ 1 - Năm học 2025-2026  
* **🏫 Trường:** VNU-HUS (Đại học Quốc gia Hà Nội - Trường Đại học Khoa học Tự nhiên)  
* **📝 Tiêu đề:** Vehicle Counting AI  
* **📅 Ngày nộp:** 30/11/2025  
* **📄 Báo cáo PDF:** 📄 [[Liên kết tới báo cáo PDF trong kho lưu trữ này](https://github.com/dekii2275/CV_trafficdetection/blob/main/baocao_ai.pdf)]  
* **🖥️ Slide thuyết trình:** 🖥️ [[Liên kết tới slide thuyết trình trong kho lưu trữ này](https://github.com/dekii2275/CV_trafficdetection/blob/main/slide_AI.pdf)]
* **📂 Kho lưu trữ:** 📁 https://github.com/dekii2275/CV_trafficdetection

**👥 Thành viên nhóm:**

| 👤 Họ và tên      | 🆔 Mã sinh viên     | 🐙 Tên GitHub        | 🛠️ Đóng góp  |
|------------------|--------------------|----------------------|----------------------|
| Nguyễn Minh Anh  | 23001495           | Dekii2275            | Counting Vehicle, Chatbot     |
| Nguyễn Trung Kiên| 23001530            | kientrung2005       | Analysis             |
| Nguyễn Thế Quang | 23001549            | thequang05           | Model                |
| Trần Đăng Tài    | 23001558            | TaiTranDang145       | Backend              |
| Nguyễn Doãn Toàn | 23001564            | DToan010605          | Frontend             |

---

## 📑 Tổng quan cấu trúc báo cáo

### Chương 1: Giới thiệu
**📝 Tóm tắt**
   - Tổng quan ngắn gọn về dự án, mục tiêu chính và kết quả nổi bật
   - Hệ thống đếm phương tiện giao thông tự động sử dụng YOLOv8m
   - Đạt mAP@0.5 = 92.49%, Precision = 85.62%, Recall = 87.95%
   - Xử lý realtime với tốc độ 25-30 FPS

**❓ Bài toán đặt ra**
   - Mô tả vấn đề quản lý và giám sát giao thông
   - Các thách thức: nhận diện 4 loại phương tiện, đếm chính xác, xử lý realtime, xây dựng hệ thống tích hợp

### Chương 2: Phương pháp & Triển khai
**⚙️ Phương pháp**
   - Lý thuyết về CNN, kiến trúc YOLOv8m
   - Phương pháp Fine-tuning từ weights pre-trained COCO
   - Các chỉ số đánh giá: IoU, Precision, Recall, mAP, F1-Score
   - Dữ liệu: 1547 ảnh với 4 lớp (Car, Motor, Truck, Bus)

**💻 Triển khai**
   - Môi trường: Python 3.10+, PyTorch, Ultralytics YOLO
   - Backend: FastAPI với REST API và WebSocket
   - Frontend: Next.js 14 với TypeScript và Tailwind CSS
   - Phân tích dữ liệu: Pipeline xử lý realtime với binary-safe tail reading
   - Đếm xe: Multiprocessing, tracking với ROI, lưu trữ JSON

### Chương 3: Kết quả & Phân tích
**📊 Kết quả & Thảo luận**
   - Kết quả huấn luyện mô hình: mAP@0.5 = 92.49%
   - Phân tích hiệu năng theo từng lớp phương tiện
   - Hiệu năng xử lý realtime: 25-30 FPS
   - Kết quả hệ thống đếm xe: độ chính xác trên 90%
   - Kết quả phân tích dữ liệu và web application

### Chương 4: Kết luận
**✅ Kết luận & Hướng phát triển**
   - 🔭 Tổng kết đóng góp: hệ thống đa tầng hoàn chỉnh
   - Hạn chế: sự khác biệt dữ liệu training và thực tế, phương tiện di chuyển nhanh
   - Hướng phát triển: cải thiện dữ liệu, Domain Adaptation, cải thiện tracking, MLOps

### Tài liệu tham khảo & Phụ lục
**📚 Tài liệu tham khảo**
   - 🔗 Danh sách bài báo, sách và nguồn tham khảo về YOLO, CNN, vehicle counting

**📎 Phụ lục** *(Tùy chọn)*
   - 📎 Kết quả bổ sung, đoạn mã hoặc hướng dẫn sử dụng

---

## 📝 Hướng dẫn nộp bài

### 📋 Yêu cầu

- **Định dạng:**  
   + 🖨️ Báo cáo phải được đánh máy, trình bày rõ ràng và xuất ra định dạng PDF (khuyến nghị dùng LaTeX).  
   + 🔁 Một bản báo cáo cần lưu trên kho GitHub của dự án, hai bản nộp trên Canvas (một cho giảng viên, một cho trợ giảng), và hai bản in (một cho giảng viên, một cho trợ giảng). Slide trình bày cũng thực hiện tương tự (không cần bản in slides).
- **Kho lưu trữ:** 📂 Bao gồm báo cáo PDF, slide, toàn bộ mã nguồn và tài liệu liên quan. Nếu vượt quá giới hạn dung lượng của GitHub, có thể tải lên Google Drive hoặc Dropbox và dẫn link trong tài liệu.
- **Làm việc nhóm:** 🤝 Cần ghi rõ đóng góp của từng thành viên trong nhóm.
- **Tài liệu hóa mã nguồn:**  
   + 🧾 Có bình luận giải thích rõ các thuật toán/phần logic phức tạp  
   + 🧪 Docstring cho hàm/phương thức mô tả tham số, giá trị trả về và mục đích  
   + 📘 File README cho từng module mã nguồn, hướng dẫn cài đặt và sử dụng  
   + 📝 Bình luận inline cho các đoạn mã không rõ ràng

### ✅ Danh sách kiểm tra trước khi nộp
- [X] ✅ Đánh dấu X vào ô để xác nhận hoàn thành  
- [X] ✍️ Điền đầy đủ các mục trong mẫu README này  
- [X] 📄 Hoàn thiện báo cáo PDF chi tiết theo cấu trúc trên  
- [X] 🎨 Tuân thủ định dạng và nội dung theo hướng dẫn giảng viên  
- [X] ➕ Thêm các mục riêng của dự án nếu cần  
- [X] 🔍 Kiểm tra lại ngữ pháp, diễn đạt và độ chính xác kỹ thuật  
- [X] ⬆️ Tải lên báo cáo PDF, slide trình bày và mã nguồn  
- [X] 🧩 Đảm bảo tất cả mã nguồn được tài liệu hóa đầy đủ với bình luận và docstring  
- [X] 🔗 Kiểm tra các liên kết và tài liệu tham khảo hoạt động đúng

### 🏆 Tiêu chí đánh giá Bài tập nhóm

Xem 📄 [Rubrics.md](Rubrics.md) để biết chi tiết về tiêu chí đánh giá bài tập nhóm, bao gồm điểm tối đa cho từng tiêu chí và mô tả các mức độ đánh giá (Xuất sắc, Tốt, Cần cải thiện).

### 📚 Liên kết hữu ích

- 📄 [Báo cáo LaTeX](main-vi.tex) - File LaTeX của báo cáo  
- 📘 [Sổ tay dùng LaTeX](https://vietex.blog.fc2.com/blog-entry-516.html) - Hướng dẫn sử dụng LaTeX bằng tiếng Việt  
- 🔎 [Một số phương pháp tải bài báo khoa học](https://hoanganhduc.github.io/misc/m%E1%BB%99t-s%E1%BB%91-ph%C6%B0%C6%A1ng-ph%C3%A1p-t%E1%BA%A3i-b%C3%A0i-b%C3%A1o-khoa-h%E1%BB%8Dc/) - Hướng dẫn một số phương pháp tải bài báo khoa học  
- 📰 [AI Vietnam Blog](https://aivietnam.edu.vn/blog) - Blog với các bài viết về AI bằng tiếng Việt
- 🚗 [Ultralytics YOLO](https://docs.ultralytics.com/) - Tài liệu chính thức về YOLOv8
- ⚡ [FastAPI Documentation](https://fastapi.tiangolo.com/) - Tài liệu FastAPI
- ⚛️ [Next.js Documentation](https://nextjs.org/docs) - Tài liệu Next.js

---

## 🎯 Tóm tắt dự án

Dự án **Vehicle Counting AI** là một hệ thống đếm phương tiện giao thông tự động sử dụng công nghệ thị giác máy tính và học sâu. Hệ thống được phát triển dựa trên mô hình YOLOv8m được fine-tuning trên tập dữ liệu phương tiện giao thông Việt Nam, đạt độ chính xác cao (mAP@0.5 = 92.49%). Hệ thống bao gồm:

- **Mô hình nhận diện:** YOLOv8m fine-tuning từ COCO weights
- **Hệ thống đếm xe realtime:** Tracking với ROI, multiprocessing
- **Pipeline phân tích dữ liệu:** Binary-safe tail reading, hotspot detection
- **Web Application:** Backend FastAPI + Frontend Next.js 14
- **Tính năng bổ sung:** AI Chatbot với RAG architecture

---

*Cập nhật lần cuối: 🗓️ Tháng 11/2025*




