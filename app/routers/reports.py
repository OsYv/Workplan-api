from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.user import User
from app.models.shift import Shift
from app.models.time_entry import TimeEntry
from app.schemas.reports import HoursRow

router = APIRouter()


def minutes_between(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


@router.get("/hours", response_model=list[HoursRow])
def hours_report(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    start_dt = datetime.combine(from_date, datetime.min.time())
    end_dt = datetime.combine(to_date, datetime.max.time())

    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    rows: list[HoursRow] = []

    for u in users:
        # Soll (geplante Minuten)
        shifts = db.query(Shift).filter(
            Shift.user_id == u.id,
            Shift.start_at >= start_dt,
            Shift.start_at <= end_dt,
        ).all()
        planned = sum(minutes_between(s.start_at, s.end_at) for s in shifts)

        # Ist (gestempelte Minuten)
        entries = db.query(TimeEntry).filter(
            TimeEntry.user_id == u.id,
            TimeEntry.clock_in >= start_dt,
            TimeEntry.clock_in <= end_dt,
            TimeEntry.clock_out.isnot(None),
        ).all()

        worked = 0
        for e in entries:
            dur = minutes_between(e.clock_in, e.clock_out)
            worked += max(0, dur - (e.break_minutes_applied or 0))

        rows.append(
            HoursRow(
                user_id=u.id,
                name=getattr(u, "name", u.email),
                planned_minutes=planned,
                worked_minutes=worked,
                overtime_minutes=worked - planned,
            )
        )

    return rows
