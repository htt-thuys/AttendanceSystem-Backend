from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class AdminLog(Base):
    """Bang admin_logs - audit trail moi hanh dong cua admin."""

    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(30), nullable=True)
    target_type = Column(String(30), nullable=True)
    target_id = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    admin = relationship("User", back_populates="admin_logs")
