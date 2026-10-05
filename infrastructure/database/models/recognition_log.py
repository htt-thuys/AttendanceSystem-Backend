from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class RecognitionLog(Base):
    """Bang recognition_logs - lich su moi lan nhan dien."""

    __tablename__ = "recognition_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    face_image_path = Column(Text, nullable=True)
    result_label = Column(String(10), nullable=True)
    top_score = Column(Float, nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    final_label = Column(String(20), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    camera = relationship("Camera", back_populates="recognition_logs")
    event = relationship("Event", back_populates="recognition_logs")
    meeting = relationship("Meeting", back_populates="recognition_logs")
    employee = relationship("Employee", back_populates="recognition_logs")
    resolver = relationship("User", foreign_keys=[resolved_by], back_populates="resolved_logs")
