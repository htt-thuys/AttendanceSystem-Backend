from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class Event(Base):
    """Bang events - khung gio dat ten de ghi nhan nguoi xuat hien."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    recognition_logs = relationship("RecognitionLog", back_populates="event")
    unknown_queue_items = relationship("UnknownQueue", back_populates="event")
    creator = relationship("User")
