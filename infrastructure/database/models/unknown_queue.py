from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Text

from infrastructure.database.models.base import Base


class UnknownQueue(Base):
    """Bang unknown_queue - hang doi mat chua nhan ra, cho admin xu ly."""

    __tablename__ = "unknown_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    image_path = Column(Text, nullable=False)
    vector = Column(ARRAY(Float), nullable=False)
    face_quality = Column(Float, nullable=True)
    attempt_count = Column(Integer, default=1, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    event = relationship("Event", back_populates="unknown_queue_items")
    meeting = relationship("Meeting", back_populates="unknown_queue_items")
    resolver = relationship("User", back_populates="resolved_unknown")
