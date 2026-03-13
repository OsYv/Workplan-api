from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimeEntryAudit(Base):
    __tablename__ = "time_entry_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time_entry_id: Mapped[int] = mapped_column(ForeignKey("time_entries.id", ondelete="CASCADE"), index=True)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    reason: Mapped[str] = mapped_column(Text, default="")

    old_clock_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    old_clock_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    old_break_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    new_clock_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_clock_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_break_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
