from database.db import get_connection
import hashlib

# ---------------- HASH PASSWORD ----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------- CREATE USER ----------------
def create_user(username: str, password: str, role: str = "user") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, hash_password(password), role)
        )
        conn.commit()
        return True
    except Exception as e:
        # IntegrityError for duplicate username
        conn.rollback()
        return False
    finally:
        conn.close()


# ---------------- LOGIN USER ----------------
def login_user(username: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, role, password FROM users WHERE username = %s",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()
    if user and user[3] == hash_password(password):
        return {"id": user[0], "username": user[1], "role": user[2]}
    return None


# ---------------- CHECK ADMIN EXISTS ----------------
def admin_exists() -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
    exists = cursor.fetchone() is not None
    conn.close()
    return exists