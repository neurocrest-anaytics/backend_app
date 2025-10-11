# backend/app/routers/auth.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3, os
import jwt  # Decoding Google JWT (signature not verified here — dev-only)

router = APIRouter(prefix="/auth", tags=["auth"])

# ✅ Database path fix (absolute path safety)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "../../paper_trading.db")

# 📦 Models
class UserIn(BaseModel):
    username: str
    password: str

class UpdatePassword(BaseModel):
    username: str
    new_password: str

class UpdateEmail(BaseModel):
    username: str
    new_email: str

class GoogleToken(BaseModel):
    token: str

# 🧠 Utility: Ensure DB and users table exist
def ensure_user_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

# ✅ Login route
@router.post("/login")
def login(user: UserIn):
    ensure_user_table()
    print(f"🔑 Login attempt: {user.username}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (user.username, user.password))
    row = cur.fetchone()
    conn.close()

    if row:
        print(f"✅ Login success for: {user.username}")
        return {"success": True, "username": user.username}
    else:
        print(f"❌ Invalid credentials for: {user.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

# ✅ Register route
@router.post("/register", status_code=200)
def register(user: UserIn):
    ensure_user_table()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (user.username,))
        if cur.fetchone():
            conn.close()
            return {"success": False, "message": "Username already exists"}

        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user.username, user.password))
        conn.commit()
        conn.close()
        print(f"🆕 Registered new user: {user.username}")
        return {"success": True, "message": "User registered successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

# ✅ Update password
@router.post("/update-password")
def update_password(data: UpdatePassword):
    ensure_user_table()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = ? WHERE username = ?", (data.new_password, data.username))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Password updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Update email (rename username)
@router.post("/update-email")
def update_email(data: UpdateEmail):
    ensure_user_table()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE users SET username = ? WHERE username = ?", (data.new_email, data.username))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Email updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Google Login
@router.post("/google-login")
def google_login(data: GoogleToken):
    ensure_user_table()
    try:
        idinfo = jwt.decode(data.token, options={"verify_signature": False})
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (email,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (email, "google"))
            conn.commit()
        conn.close()

        return {"success": True, "username": email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google login failed: {str(e)}")
