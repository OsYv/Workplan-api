from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.time_entry import TimeEntry
from app.models.time_entry_audit import TimeEntryAudit
from app.schemas.time_entry import TimeEntryAdminPatch, TimeEntryOut

router = APIRouter()


@router.patch("/{time_entry_id}", response_model=TimeEntryOut)
def admin_patch_time_entry(
    time_entry_id: int,
    payload: TimeEntryAdminPatch,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    te = db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
    if not te:
        raise HTTPException(status_code=404, detail="Time entry not found")

    # Basic validation
    new_clock_in = payload.clock_in if payload.clock_in is not None else te.clock_in
    new_clock_out = payload.clock_out if payload.clock_out is not None else te.clock_out
    if new_clock_out is not None and new_clock_out <= new_clock_in:
        raise HTTPException(status_code=422, detail="clock_out must be after clock_in")

    # Audit speichern
    audit = TimeEntryAudit(
        time_entry_id=te.id,
        changed_by_user_id=admin.id,
        reason=payload.reason or "admin correction",
        old_clock_in=te.clock_in,
        old_clock_out=te.clock_out,
        old_break_minutes=te.break_minutes_applied,
        new_clock_in=payload.clock_in if payload.clock_in is not None else te.clock_in,
        new_clock_out=payload.clock_out if payload.clock_out is not None else te.clock_out,
        new_break_minutes=payload.break_minutes_applied if payload.break_minutes_applied is not None else te.break_minutes_applied,
    )
    db.add(audit)

    # Werte aktualisieren
    if payload.clock_in is not None:
        te.clock_in = payload.clock_in
    if payload.clock_out is not None:
        te.clock_out = payload.clock_out
    if payload.break_minutes_applied is not None:
        te.break_minutes_applied = payload.break_minutes_applied

    te.source = "admin_edit"

    db.commit()
    db.refresh(te)
    return te
