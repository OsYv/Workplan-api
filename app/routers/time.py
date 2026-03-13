from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from typing import List
from fastapi import Query

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.time_entry import TimeEntry
from app.models.shift import Shift, ShiftType
from app.models.user import User
from app.schemas.time_entry import ClockInRequest, TimeEntryOut

router = APIRouter()
log = logging.getLogger("workplan.time")


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xrip = request.headers.get("x-real-ip")
    if xrip:
        return xrip.strip()
    return request.client.host if request.client else "unknown"


def _diag(request: Request, user: Optional[User]) -> Dict[str, Any]:
    return {
        "method": request.method,
        "path": request.url.path,
        "host": request.headers.get("host"),
        "origin": request.headers.get("origin"),
        "referer": request.headers.get("referer"),
        "proto": request.headers.get("x-forwarded-proto"),
        "xff": request.headers.get("x-forwarded-for"),
        "xri": request.headers.get("x-real-ip"),
        "client_ip": _client_ip(request),
        "user_id": getattr(user, "id", None),
        "user_email": getattr(user, "email", None),
    }


def _get_open_entry(db: Session, user_id: int) -> Optional[TimeEntry]:
    """Zentraler Filter: 'offener' Eintrag = clock_out IS NULL."""
    return (
        db.query(TimeEntry)
        .filter(TimeEntry.user_id == user_id)
        .filter(TimeEntry.clock_out.is_(None))
        .order_by(TimeEntry.clock_in.desc())
        .first()
    )


@router.get("/status")
def get_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        open_entry = _get_open_entry(db, current_user.id)

        if not open_entry:
            log.info("time.status -> not clocked in | %s", _diag(request, current_user))
            return {"is_clocked_in": False, "time_entry": None}

        log.info(
            "time.status -> clocked in entry_id=%s | %s",
            open_entry.id,
            _diag(request, current_user),
        )
        return {
            "is_clocked_in": True,
            "time_entry": {
                "id": open_entry.id,
                "user_id": open_entry.user_id,
                "shift_id": open_entry.shift_id,
                "clock_in": open_entry.clock_in,
                "clock_out": open_entry.clock_out,
                "break_minutes_applied": open_entry.break_minutes_applied,
                "source": open_entry.source,
                "status": open_entry.status,
            },
        }

    except Exception:
        log.exception("time.status -> 500 | %s", _diag(request, current_user))
        raise


@router.post("/clock-in", response_model=TimeEntryOut)
def clock_in(
    body: ClockInRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        open_entry = _get_open_entry(db, user.id)
        if open_entry:
            log.warning(
                "time.clock_in -> already clocked in entry_id=%s | %s",
                open_entry.id,
                _diag(request, user),
            )
            raise HTTPException(status_code=409, detail="Already clocked in")

        # shift_id optional validieren (muss dem User gehören)
        if body.shift_id is not None:
            shift = db.get(Shift, body.shift_id)
            if not shift or shift.user_id != user.id:
                log.warning(
                    "time.clock_in -> invalid shift_id=%s | %s",
                    body.shift_id,
                    _diag(request, user),
                )
                raise HTTPException(status_code=400, detail="Invalid shift_id")

        entry = TimeEntry(
            user_id=user.id,
            shift_id=body.shift_id,
            clock_in=datetime.now(timezone.utc),
            clock_out=None,
            status="open",
            break_minutes_applied=0,
            source="clock",
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)

        log.info("time.clock_in -> OK entry_id=%s | %s", entry.id, _diag(request, user))
        return entry

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        log.exception("time.clock_in -> 500 (rolled back) | %s", _diag(request, user))
        raise


@router.post("/clock-out", response_model=TimeEntryOut)
def clock_out(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Clock-out hat bewusst keinen Body."""
    try:
        # Row-Lock gegen Race-Conditions (z.B. 2 Tabs / Doppelklick)
        entry = (
            db.query(TimeEntry)
            .filter(TimeEntry.user_id == user.id)
            .filter(TimeEntry.clock_out.is_(None))
            .order_by(TimeEntry.clock_in.desc())
            .with_for_update()
            .first()
        )

        if not entry:
            log.warning("time.clock_out -> not clocked in | %s", _diag(request, user))
            raise HTTPException(status_code=409, detail="Not clocked in")

        # Extra-Schutz (falls ein anderer Request zwischenzeitlich closed hat)
        if entry.clock_out is not None:
            log.warning(
                "time.clock_out -> already clocked out entry_id=%s | %s",
                entry.id,
                _diag(request, user),
            )
            raise HTTPException(status_code=409, detail="Already clocked out")

        # Pausenminuten aus ShiftType (optional)
        break_minutes = 0
        if entry.shift_id is not None:
            shift = db.get(Shift, entry.shift_id)
            if not shift:
                log.warning(
                    "time.clock_out -> shift missing shift_id=%s entry_id=%s | %s",
                    entry.shift_id,
                    entry.id,
                    _diag(request, user),
                )
            else:
                st = db.get(ShiftType, shift.shift_type_id)
                if st and st.break_minutes_default is not None:
                    break_minutes = int(st.break_minutes_default)

        entry.clock_out = datetime.now(timezone.utc)
        entry.break_minutes_applied = break_minutes
        entry.status = "closed"

        db.commit()
        db.refresh(entry)

        log.info(
            "time.clock_out -> OK entry_id=%s break=%s | %s",
            entry.id,
            break_minutes,
            _diag(request, user),
        )
        return entry

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        log.exception("time.clock_out -> 500 (rolled back) | %s", _diag(request, user))
        raise
@router.get("/history", response_model=list[TimeEntryOut])
def history(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
):
    try:
        items = (
            db.query(TimeEntry)
            .filter(TimeEntry.user_id == user.id)
            .order_by(TimeEntry.clock_in.desc())
            .limit(limit)
            .all()
        )

        log.info("time.history -> OK limit=%s count=%s | %s", limit, len(items), _diag(request, user))
        return items

    except Exception:
        log.exception("time.history -> 500 | %s", _diag(request, user))
        raise
