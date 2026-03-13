from pydantic import BaseModel


class HoursRow(BaseModel):
    user_id: int
    name: str
    planned_minutes: int
    worked_minutes: int
    overtime_minutes: int
