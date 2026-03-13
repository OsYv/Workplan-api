from pydantic import BaseModel


class ShiftCreate(BaseModel):
    user_id: int
    shift_type_id: int
    date: str
    start_time: str
    end_time: str
    is_flexible: bool = False
    notes: str | None = None


class ShiftUpdate(BaseModel):
    user_id: int | None = None
    shift_type_id: int | None = None
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_flexible: bool | None = None
    notes: str | None = None


class ShiftOut(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None

    shift_type_id: int
    shift_type_name: str | None = None
    shift_type_color: str | None = None
    shift_type_counts_as_work: bool | None = None

    date: str
    start_time: str
    end_time: str
    is_flexible: bool
    notes: str | None = None