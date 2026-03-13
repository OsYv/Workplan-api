from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class ClockInRequest(BaseModel):
    shift_id: int | None = None


class TimeEntryAdminPatch(BaseModel):
    clock_in: datetime | None = None
    clock_out: datetime | None = None
    break_minutes_applied: int | None = None
    reason: str = "admin correction"


class TimeEntryOut(BaseModel):
    id: int
    user_id: int
    shift_id: Optional[int]
    clock_in: datetime
    clock_out: Optional[datetime]
    break_minutes_applied: int
    source: str
    
    class Config:
        from_attributes = True
