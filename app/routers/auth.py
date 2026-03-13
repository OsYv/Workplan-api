from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Request, Form, Cookie
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, create_token, decode_token
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import TokenOut
from app.schemas.users import UserMeOut

router = APIRouter()


@router.get("/me", response_model=UserMeOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


def _is_https(request: Request) -> bool:
    """
    Reverse Proxy (Synology / nginx): HTTPS wird oft via x-forwarded-proto signalisiert.
    """
    xf_proto = request.headers.get("x-forwarded-proto", "")
    return xf_proto.lower() == "https"


@router.post("/login", response_model=TokenOut)
def login(
    request: Request,
    response: Response,
    username: str = Form(...),         # Swagger: "username" -> bei dir E-Mail
    password: str = Form(...),
    remember_me: bool = Form(False),   # Checkbox im Frontend
    db: Session = Depends(get_db),
):
    email = username.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Access Token immer
    access = create_token(
        str(user.id),
        "access",
        timedelta(minutes=settings.JWT_ACCESS_MINUTES),
    )

    # Refresh Token nur bei remember_me -> als HttpOnly Cookie
    refresh_token: Optional[str] = None
    if remember_me:
        refresh_token = create_token(
            str(user.id),
            "refresh",  # <-- WICHTIG: refresh, nicht access
            timedelta(days=settings.JWT_REFRESH_DAYS),
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=_is_https(request),          # hinter HTTPS Reverse Proxy True
            samesite="lax",
            max_age=settings.JWT_REFRESH_DAYS * 24 * 60 * 60,
            path="/",
        )
    else:
        # Optional: falls vorher ein Cookie gesetzt war, beim "nicht merken" entfernen
        response.delete_cookie("refresh_token", path="/")

    # Sicherer wäre: refresh_token NICHT im Body zurückgeben.
    # Wenn dein Frontend/Schema es braucht, bleibt es hier optional drin.
    return TokenOut(access_token=access, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # neue Tokens
    access = create_token(
        str(user_id),
        "access",
        timedelta(minutes=settings.JWT_ACCESS_MINUTES),
    )
    new_refresh = create_token(
        str(user_id),
        "refresh",
        timedelta(days=settings.JWT_REFRESH_DAYS),
    )

    # Cookie rotieren
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=_is_https(request),
        samesite="lax",
        max_age=settings.JWT_REFRESH_DAYS * 24 * 60 * 60,
        path="/",
    )

    # Wieder: refresh Token im Body eigentlich weglassen.
    return TokenOut(access_token=access, refresh_token=None)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}