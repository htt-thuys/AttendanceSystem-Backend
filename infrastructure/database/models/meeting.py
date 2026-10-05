from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class Meeting(Base):
    """Bang meetings - thong tin cuoc hop."""

    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    location = Column(Text, nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    status = Column(String(20), default="scheduled", nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    participants = relationship(
        "MeetingParticipant",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
    camera = relationship("Camera", back_populates="meetings")
    creator = relationship("User", back_populates="created_meetings")
    recognition_logs = relationship("RecognitionLog", back_populates="meeting")
    unknown_queue_items = relationship("UnknownQueue", back_populates="meeting")
