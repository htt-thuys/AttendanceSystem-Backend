from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class FaceVector(Base):
    """Bang face_vectors - metadata cua tung vector khuon mat."""

    __tablename__ = "face_vectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    qdrant_point_id = Column(Integer, unique=True, nullable=False)
    source = Column(String(20), nullable=True)
    source_image_path = Column(Text, nullable=False)
    quality_score = Column(Float, nullable=True)
    score_at_create = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employee = relationship("Employee", back_populates="face_vectors")
