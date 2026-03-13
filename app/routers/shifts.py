from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, get_current_user, require_admin
from app.models.shift import Shift, ShiftType
from app.models.user import User
from app.schemas.shifts import ShiftCreate, ShiftOut, ShiftUpdate

router = APIRouter()


def _validate_times(start_time: str, end_time: str):
    if len(start_time) != 5 or len(end_time) != 5:
        raise HTTPException(status_code=422, detail="Time format must be HH:MM")

    if start_time >= end_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")


def _user_display(user: User) -> str | None:
    first_name = getattr(user, "first_name", None) or ""
    last_name = getattr(user, "last_name", None) or ""
    full_name = f"{first_name} {last_name}".strip()

    if full_name:
        return full_name

    if getattr(user, "name", None):
        return user.name

    return getattr(user, "email", None)


def _serialize_shift(shift: Shift) -> ShiftOut:
    return ShiftOut(
        id=shift.id,
        user_id=shift.user_id,
        user_name=_user_display(shift.user) if shift.user else None,
        shift_type_id=shift.shift_type_id,
        shift_type_name=getattr(shift.shift_type, "name", None),
        shift_type_color=getattr(shift.shift_type, "color", None),
        shift_type_counts_as_work=getattr(shift.shift_type, "counts_as_work", None),
        date=shift.date,
        start_time=shift.start_time,
        end_time=shift.end_time,
        is_flexible=shift.is_flexible,
        notes=shift.notes,
    )


@router.post("", response_model=ShiftOut)
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    shift_type = db.get(ShiftType, payload.shift_type_id)
    if not shift_type:
        raise HTTPException(status_code=404, detail="Shift type not found")

    _validate_times(payload.start_time, payload.end_time)

    shift = Shift(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)

    shift = (
        db.query(Shift)
        .options(joinedload(Shift.user), joinedload(Shift.shift_type))
        .filter(Shift.id == shift.id)
        .first()
    )

    return _serialize_shift(shift)


@router.get("", response_model=list[ShiftOut])
def list_shifts(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    user_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    q = (
        db.query(Shift)
        .options(joinedload(Shift.user), joinedload(Shift.shift_type))
        .filter(Shift.date >= from_date, Shift.date <= to_date)
    )

    if user_id is not None:
        q = q.filter(Shift.user_id == user_id)

    items = q.order_by(Shift.date.asc(), Shift.start_time.asc()).all()
    return [_serialize_shift(s) for s in items]


@router.get("/me", response_model=list[ShiftOut])
def my_shifts(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = (
        db.query(Shift)
        .options(joinedload(Shift.user), joinedload(Shift.shift_type))
        .filter(
            Shift.user_id == current_user.id,
            Shift.date >= from_date,
            Shift.date <= to_date,
        )
    )

    items = q.order_by(Shift.date.asc(), Shift.start_time.asc()).all()
    return [_serialize_shift(s) for s in items]


@router.put("/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    update_data = payload.model_dump(exclude_unset=True)

    new_start = update_data.get("start_time", shift.start_time)
    new_end = update_data.get("end_time", shift.end_time)
    _validate_times(new_start, new_end)

    if "user_id" in update_data:
        user = db.get(User, update_data["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    if "shift_type_id" in update_data:
        shift_type = db.get(ShiftType, update_data["shift_type_id"])
        if not shift_type:
            raise HTTPException(status_code=404, detail="Shift type not found")

    for key, value in update_data.items():
        setattr(shift, key, value)

    db.commit()
    db.refresh(shift)

    shift = (
        db.query(Shift)
        .options(joinedload(Shift.user), joinedload(Shift.shift_type))
        .filter(Shift.id == shift.id)
        .first()
    )

    return _serialize_shift(shift)


@router.delete("/{shift_id}")
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    db.delete(shift)
    db.commit()
    return {"ok": True}