from datetime import date, time
from typing import Optional

from pydantic import BaseModel


class ShiftPlanBase(BaseModel):
    shift_type_id: int
    date: date
    start_time: time
    end_time: time
    break_minutes: int = 0
    note: Optional[str] = None
    status: str = "planned"


class ShiftPlanCreate(ShiftPlanBase):
    user_id: int


class ShiftPlanUpdate(BaseModel):
    user_id: Optional[int] = None
    shift_type_id: Optional[int] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_minutes: Optional[int] = None
    note: Optional[str] = None
    status: Optional[str] = None


class ShiftPlanOut(ShiftPlanBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True