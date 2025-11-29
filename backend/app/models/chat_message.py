from sqlalchemy import Column, Integer, String, JSON, DateTime, Text
from sqlalchemy.sql import func
from app.db.base import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    # 1. QUAN TRỌNG: Phải có Session ID để gom nhóm cuộc hội thoại
    # Index=True để query lịch sử cho nhanh
    session_id = Column(String, index=True, nullable=False)
    # 2. CHUẨN LLM: Dùng 'role' thay vì 'is_user'
    # Giá trị: "user" | "assistant" | "system"
    role = Column(String, nullable=False) 
    # 3. Dùng Text thay vì String cho nội dung dài
    content = Column(Text, nullable=False)
    # 4. Dữ liệu đặc thù cho RAG (Lưu nguồn trích dẫn)
    # Lưu danh sách các văn bản luật đã tham khảo để trả lời câu này
    sources = Column(JSON, nullable=True) 
    # 5. Hình ảnh (Nếu chat có upload ảnh hoặc AI trả về ảnh)
    images = Column(JSON, nullable=True)
    # Metadata khác (Thời gian phản hồi, token usage...)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())