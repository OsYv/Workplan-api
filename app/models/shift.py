from sqlalchemy import String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ShiftType(Base):
    __tablename__ = "shift_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    break_minutes_default: Mapped[int] = mapped_column(Integer, default=0)

    fixed_start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)   # "08:00"
    fixed_end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)     # "17:00"
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)             # "#2563eb"

    counts_as_work: Mapped[bool] = mapped_column(Boolean, default=True)
    is_flexible_default: Mapped[bool] = mapped_column(Boolean, default=False)


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[str] = mapped_column(String(10))       # YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(5))  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5))    # HH:MM
    shift_type_id: Mapped[int] = mapped_column(ForeignKey("shift_types.id"))
    is_flexible: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User")
    shift_type = relationship("ShiftType")