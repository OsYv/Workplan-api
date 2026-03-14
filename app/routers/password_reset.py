from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Session, Mapped, mapped_column

from app.core.deps import get_db, get_current_user, require_admin
from app.core.security import get_password_hash
from app.db.base import Base
from app.models.user import User

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter()

# ── Konfiguration ────────────────────────────────────────────────────────────

SMTP_HOST = "smtp.oswald-it.ch"
SMTP_PORT = 465
SMTP_USER = "passwort@oswald-it.ch"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # In .env auslagern!
SMTP_FROM = "Workplan <passwort@oswald-it.ch>"

RESET_TOKEN_EXPIRE_MINUTES = 60
FRONTEND_URL = "https://workplan.oswald-it.ch"  # Deine Frontend-URL anpassen


# ── Modell für Reset-Tokens ──────────────────────────────────────────────────

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column()
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)


# ── Schemas ──────────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class AdminSetPasswordRequest(BaseModel):
    new_password: str


# ── E-Mail Hilfsfunktion ─────────────────────────────────────────────────────

def send_reset_email(to_email: str, reset_link: str, user_name: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Workplan – Passwort zurücksetzen"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    text = f"""Hallo {user_name},

Du hast eine Anfrage zum Zurücksetzen deines Passworts gestellt.

Klicke auf folgenden Link um dein Passwort zurückzusetzen:
{reset_link}

Dieser Link ist 60 Minuten gültig.

Falls du diese Anfrage nicht gestellt hast, kannst du diese E-Mail ignorieren.

Mit freundlichen Grüssen
Workplan by Oswald-IT
"""

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #15803d; padding: 20px; border-radius: 12px 12px 0 0; text-align: center;">
    <h1 style="color: white; margin: 0; font-size: 24px;">Workplan</h1>
  </div>
  <div style="background: white; border: 1px solid #e2e8f0; padding: 30px; border-radius: 0 0 12px 12px;">
    <p style="color: #334155;">Hallo <strong>{user_name}</strong>,</p>
    <p style="color: #334155;">Du hast eine Anfrage zum Zurücksetzen deines Passworts gestellt.</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="{reset_link}"
         style="background: #15803d; color: white; padding: 14px 28px; border-radius: 10px;
                text-decoration: none; font-weight: bold; font-size: 16px;">
        Passwort zurücksetzen
      </a>
    </div>
    <p style="color: #64748b; font-size: 14px;">Dieser Link ist <strong>60 Minuten</strong> gültig.</p>
    <p style="color: #64748b; font-size: 14px;">Falls du diese Anfrage nicht gestellt hast, kannst du diese E-Mail ignorieren.</p>
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
    <p style="color: #94a3b8; font-size: 12px; text-align: center;">Workplan by Oswald-IT</p>
  </div>
</body>
</html>
"""

    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())


# ── Endpunkte ────────────────────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """E-Mail mit Reset-Link senden. Gibt immer 200 zurück (kein User-Enumeration)."""
    user = db.query(User).filter(
        User.email == payload.email.lower().strip()
    ).first()

    if user and user.is_active:
        # Alte Token für diesen User löschen
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,  # noqa: E712
        ).delete()

        # Neuen Token erstellen
        token = secrets.token_urlsafe(48)
        expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expires,
            used=False,
        )
        db.add(reset_token)
        db.commit()

        # Name für E-Mail
        user_name = (
            f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
            or user.name
            or user.email
        )

        reset_link = f"{FRONTEND_URL}/passwort-reset?token={token}"

        # E-Mail im Hintergrund senden
        background_tasks.add_task(send_reset_email, user.email, reset_link, user_name)

    return {"ok": True, "message": "Falls die E-Mail-Adresse existiert, wurde ein Link gesendet."}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Passwort mit Token zurücksetzen."""
    now = datetime.utcnow()

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == payload.token,
        PasswordResetToken.used == False,  # noqa: E712
        PasswordResetToken.expires_at > now,
    ).first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Benutzer nicht gefunden")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 8 Zeichen haben")

    user.password_hash = get_password_hash(payload.new_password)
    reset_token.used = True
    db.commit()

    return {"ok": True, "message": "Passwort erfolgreich geändert"}


@router.post("/admin/set-password/{user_id}")
def admin_set_password(
    user_id: int,
    payload: AdminSetPasswordRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Admin setzt Passwort direkt für einen Benutzer."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 8 Zeichen haben")

    user.password_hash = get_password_hash(payload.new_password)
    db.commit()

    return {"ok": True, "message": f"Passwort für {user.email} gesetzt"}
