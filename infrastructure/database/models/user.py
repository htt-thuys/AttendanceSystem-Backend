from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from infrastructure.database.models.base import Base


class User(Base):
    """Bang users - tai khoan dang nhap."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(Text, unique=True, nullable=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="employee", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    employee_id = Column(
        Integer,
        ForeignKey("employees.id", use_alter=True, name="fk_user_employee_id"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employee = relationship(
        "Employee",
        foreign_keys=[employee_id],
        back_populates="user_account",
    )
    created_employees = relationship(
        "Employee",
        foreign_keys="[Employee.created_by]",
        back_populates="creator",
    )
    resolved_unknown = relationship("UnknownQueue", back_populates="resolver")
    resolved_logs = relationship("RecognitionLog", back_populates="resolver")
    admin_logs = relationship("AdminLog", back_populates="admin")
    updated_settings = relationship("SystemSetting", back_populates="updater")
    created_meetings = relationship("Meeting", back_populates="creator")
    notifications = relationship("Notification", back_populates="user")
