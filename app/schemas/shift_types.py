from pydantic import BaseModel


class ShiftTypeCreate(BaseModel):
    name: str
    break_minutes_default: int = 0
    fixed_start_time: str | None = None
    fixed_end_time: str | None = None
    color: str | None = None
    counts_as_work: bool = True
    is_flexible_default: bool = False


class ShiftTypeUpdate(BaseModel):
    name: str | None = None
    break_minutes_default: int | None = None
    fixed_start_time: str | None = None
    fixed_end_time: str | None = None
    color: str | None = None
    counts_as_work: bool | None = None
    is_flexible_default: bool | None = None


class ShiftTypeOut(BaseModel):
    id: int
    name: str
    break_minutes_default: int
    fixed_start_time: str | None = None
    fixed_end_time: str | None = None
    color: str | None = None
    counts_as_work: bool
    is_flexible_default: bool

    class Config:
        from_attributes = True