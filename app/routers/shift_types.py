from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.shift import ShiftType
from app.schemas.shift_types import ShiftTypeCreate, ShiftTypeOut, ShiftTypeUpdate

router = APIRouter()


@router.get("", response_model=list[ShiftTypeOut])
def list_shift_types(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(ShiftType).order_by(ShiftType.id.asc()).all()


@router.post("", response_model=ShiftTypeOut)
def create_shift_type(
    payload: ShiftTypeCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    exists = db.query(ShiftType).filter(ShiftType.name == payload.name.strip()).first()
    if exists:
        raise HTTPException(status_code=409, detail="Shift type already exists")

    st = ShiftType(
        name=payload.name.strip(),
        break_minutes_default=payload.break_minutes_default,
        fixed_start_time=payload.fixed_start_time,
        fixed_end_time=payload.fixed_end_time,
        color=payload.color,
        counts_as_work=payload.counts_as_work,
        is_flexible_default=payload.is_flexible_default,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


@router.put("/{shift_type_id}", response_model=ShiftTypeOut)
def update_shift_type(
    shift_type_id: int,
    payload: ShiftTypeUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    st = db.query(ShiftType).filter(ShiftType.id == shift_type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Shift type not found")

    if payload.name is not None:
        new_name = payload.name.strip()
        exists = (
            db.query(ShiftType)
            .filter(ShiftType.name == new_name, ShiftType.id != shift_type_id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="Shift type already exists")
        st.name = new_name

    if payload.break_minutes_default is not None:
        st.break_minutes_default = payload.break_minutes_default

    if payload.fixed_start_time is not None:
        st.fixed_start_time = payload.fixed_start_time

    if payload.fixed_end_time is not None:
        st.fixed_end_time = payload.fixed_end_time

    if payload.color is not None:
        st.color = payload.color

    if payload.counts_as_work is not None:
        st.counts_as_work = payload.counts_as_work

    if payload.is_flexible_default is not None:
        st.is_flexible_default = payload.is_flexible_default

    db.commit()
    db.refresh(st)
    return st


@router.delete("/{shift_type_id}")
def delete_shift_type(
    shift_type_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    st = db.query(ShiftType).filter(ShiftType.id == shift_type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Shift type not found")

    db.delete(st)
    db.commit()
    return {"ok": True}