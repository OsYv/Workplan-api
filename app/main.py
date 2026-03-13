from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, time, exports, users, shift_types, shifts, reports, time_entry

app = FastAPI(title="Workplan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://workplan.oswald-it.ch",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(time.router, prefix="/time", tags=["time"])
app.include_router(exports.router, prefix="/exports", tags=["exports"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(shift_types.router, prefix="/shift-types", tags=["shift_types"])
app.include_router(shifts.router, prefix="/shifts", tags=["shifts"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(time_entry.router, prefix="/time-entries", tags=["time_entries"])


@app.get("/health")
def health():
    return {"ok": True}