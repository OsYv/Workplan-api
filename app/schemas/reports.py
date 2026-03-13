from pydantic import BaseModel
from typing import Optional


class HoursRow(BaseModel):
    user_id: int
    name: str
    planned_minutes: int
    worked_minutes: int
    overtime_minutes: int


class MonthlyEntryRow(BaseModel):
    date: str
    clock_in: str
    clock_out: Optional[str] = None
    break_minutes: int
    net_minutes: int
    shift_type_name: Optional[str] = None
    shift_type_color: Optional[str] = None
    counts_as_work: bool


class MonthlyUserReport(BaseModel):
    user_id: int
    user_name: str
    year: int
    month: int
    total_work_minutes: int
    total_break_minutes: int
    total_entries: int
    entries: list[MonthlyEntryRow]
