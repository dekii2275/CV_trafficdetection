from sqlalchemy import Column, Integer, DateTime, Float, Index
from sqlalchemy.sql import func
from app.db.base import Base

class TrafficLog(Base):
    __tablename__ = "traffic_logs"

    # 1. Khóa chính (Tự tăng)
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    count_car = Column(Integer, default=0)
    count_motor = Column(Integer, default=0)
    count_bus = Column(Integer, default=0)
    count_truck = Column(Integer, default=0)
    total_vehicles = Column(Integer, default=0)
    fps = Column(Float, default=0.0)
    __table_args__ = (
        Index('idx_camera_timestamp', 'camera_id', 'timestamp'),
    )