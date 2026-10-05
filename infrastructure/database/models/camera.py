from sqlalchemy import Boolean, Column, Integer, Text
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class Camera(Base):
    """Bang cameras - thong tin camera cham cong."""

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    recognition_logs = relationship("RecognitionLog", back_populates="camera")
    meetings = relationship("Meeting", back_populates="camera")
