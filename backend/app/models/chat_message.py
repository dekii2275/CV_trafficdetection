from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Không dùng user nữa → bỏ FK + bỏ user_id
    # Nếu cần phân biệt nhiều client, ta sẽ thêm session_id / device_id sau
    # user_id = Column(Integer, ForeignKey("users.id"))

    message = Column(String, nullable=False)
    is_user = Column(Integer, nullable=False, default=1)
    images = Column(JSON, nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
