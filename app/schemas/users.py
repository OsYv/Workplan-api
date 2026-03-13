from datetime import date
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: date | None = None
    email: EmailStr
    password: str
    role: str = "employee"
    is_active: bool = True


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserMeOut(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        from_attributes = True