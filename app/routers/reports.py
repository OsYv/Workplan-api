from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin, get_current_user
from app.models.user import User
from app.models.shift import Shift, ShiftType
from app.models.time_entry import TimeEntry
from app.schemas.reports import HoursRow, MonthlyEntryRow, MonthlyUserReport

router = APIRouter()


def minutes_between(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def _build_monthly_report(
    user: User,
    year: int,
    month: int,
    db: Session,
) -> MonthlyUserReport:
    """Erstellt den Monatsbericht für einen einzelnen Benutzer."""

    # Zeitraum berechnen
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59)

    # Schichten für den Monat laden (für Schichttyp-Infos)
    shifts = (
        db.query(Shift)
        .filter(
            Shift.user_id == user.id,
            Shift.date >= f"{year:04d}-{month:02d}-01",
            Shift.date <= f"{year:04d}-{month:02d}-{last_day:02d}",
        )
        .all()
    )

    # Schichten nach Datum indexieren
    shifts_by_date: dict[str, list[Shift]] = {}
    for s in shifts:
        shifts_by_date.setdefault(s.date, []).append(s)

    # Zeiteinträge für den Monat laden
    entries = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.user_id == user.id,
            TimeEntry.clock_in >= start_dt,
            TimeEntry.clock_in <= end_dt,
        )
        .order_by(TimeEntry.clock_in)
        .all()
    )

    total_work_minutes = 0
    total_break_minutes = 0
    entry_rows: list[MonthlyEntryRow] = []

    for e in entries:
        date_str = e.clock_in.strftime("%Y-%m-%d")
        break_min = e.break_minutes_applied or 0

        # Netto-Arbeitszeit berechnen
        if e.clock_out:
            raw_min = minutes_between(e.clock_in, e.clock_out)
            net_min = max(0, raw_min - break_min)
        else:
            net_min = 0

        # Schichttyp für diesen Tag ermitteln
        day_shifts = shifts_by_date.get(date_str, [])
        first_shift = day_shifts[0] if day_shifts else None
        shift_type: ShiftType | None = first_shift.shift_type if first_shift else None

        counts_as_work = True
        if shift_type is not None:
            counts_as_work = shift_type.counts_as_work

        if counts_as_work and e.clock_out:
            total_work_minutes += net_min
            total_break_minutes += break_min

        entry_rows.append(
            MonthlyEntryRow(
                date=date_str,
                clock_in=e.clock_in.strftime("%Y-%m-%dT%H:%M:%S"),
                clock_out=e.clock_out.strftime("%Y-%m-%dT%H:%M:%S") if e.clock_out else None,
                break_minutes=break_min,
                net_minutes=net_min,
                shift_type_name=shift_type.name if shift_type else None,
                shift_type_color=shift_type.color if shift_type else None,
                counts_as_work=counts_as_work,
            )
        )

    user_name = (
        f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
        or getattr(user, "name", None)
        or user.email
    )

    return MonthlyUserReport(
        user_id=user.id,
        user_name=user_name,
        year=year,
        month=month,
        total_work_minutes=total_work_minutes,
        total_break_minutes=total_break_minutes,
        total_entries=len(entries),
        entries=entry_rows,
    )


# ── Bestehender Endpunkt (unverändert) ──────────────────────────────────────

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
        shifts = db.query(Shift).filter(
            Shift.user_id == u.id,
            Shift.date >= from_date.isoformat(),
            Shift.date <= to_date.isoformat(),
        ).all()

        planned = 0
        for s in shifts:
            try:
                sh, sm = map(int, s.start_time.split(":"))
                eh, em = map(int, s.end_time.split(":"))
                planned += (eh * 60 + em) - (sh * 60 + sm)
            except Exception:
                pass

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


# ── Neue Monats-Endpunkte ────────────────────────────────────────────────────

@router.get("/monthly", response_model=list[MonthlyUserReport])
def monthly_report_all(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Monatsbericht für alle aktiven Mitarbeiter (nur Admin)."""
    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    return [_build_monthly_report(u, year, month, db) for u in users]


@router.get("/monthly/{user_id}", response_model=MonthlyUserReport)
def monthly_report_user(
    user_id: int,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Monatsbericht für einen einzelnen Mitarbeiter.
    Admins dürfen jeden abfragen, normale User nur sich selbst."""
    is_admin = getattr(current_user, "role", None) == "admin"

    if not is_admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Kein Zugriff")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    return _build_monthly_report(user, year, month, db)
