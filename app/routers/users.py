from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.users import UserCreate, UserOut, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    email = payload.email.lower().strip()
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already exists")

    full_name = f"{payload.first_name.strip()} {payload.last_name.strip()}".strip()

    user = User(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        birth_date=payload.birth_date,
        name=full_name,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.first_name is not None:
        user.first_name = payload.first_name.strip()

    if payload.last_name is not None:
        user.last_name = payload.last_name.strip()

    if payload.birth_date is not None:
        user.birth_date = payload.birth_date

    if payload.email is not None:
        email = payload.email.lower().strip()
        exists = (
            db.query(User)
            .filter(User.email == email, User.id != user_id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="Email already exists")
        user.email = email

    if payload.password is not None:
        pw = payload.password.strip()
        if not pw:
            raise HTTPException(status_code=422, detail="Password must not be empty")
        user.password_hash = hash_password(pw)

    if payload.role is not None:
        user.role = payload.role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    user.name = full_name or user.name

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="The last admin user cannot be deleted",
            )

    db.delete(user)
    db.commit()
    return {"ok": True}