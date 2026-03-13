from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
import csv
import io
from app.core.deps import get_db, require_admin
from app.models.time_entry import TimeEntry
from app.models.user import User

router = APIRouter()

def month_range_utc(year: int, month: int):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end

@router.get("/payroll")
def export_payroll(year: int, month: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    start, end = month_range_utc(year, month)

    rows = db.query(TimeEntry, User).join(User, User.id == TimeEntry.user_id).filter(
        and_(TimeEntry.clock_in >= start, TimeEntry.clock_in < end)
    ).order_by(User.name, TimeEntry.clock_in).all()

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Mitarbeiter", "E-Mail", "Clock-in (UTC)", "Clock-out (UTC)", "Pause (min)", "Arbeitszeit netto (min)", "Status"])

    for te, u in rows:
        clock_out = te.clock_out
        net_minutes = ""
        if clock_out:
            total = int((clock_out - te.clock_in).total_seconds() // 60)
            net_minutes = max(0, total - (te.break_minutes_applied or 0))
        writer.writerow([
            u.name, u.email,
            te.clock_in.isoformat(),
            clock_out.isoformat() if clock_out else "",
            te.break_minutes_applied or 0,
            net_minutes,
            te.status
        ])

    out.seek(0)
    filename = f"payroll_{year}-{month:02d}.csv"
    return StreamingResponse(
        iter([out.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
