from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models.user import User

db = SessionLocal()
u = User(
    first_name="Yves",
    last_name="Oswald",
    birth_date="14.06.1991",
    email="y.oswald@gmx.ch",
    password_hash=hash_password("-Workplan+160893"),
    role="admin",
    is_active=True,
)
db.add(u)
db.commit()
print("created", u.email)
