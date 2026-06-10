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
        # IntegrityError for duplicate username (or other errors)
        conn.rollback()
        return False
    finally:
        conn.close()


# ---------------- LOGIN USER (dictionary access) ----------------
def login_user(username: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, role, password FROM users WHERE username = %s",
        (username,)
    )
    user = cursor.fetchone()   # returns a dictionary with column names as keys
    conn.close()
    if user and user["password"] == hash_password(password):
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }
    return None


# ---------------- CHECK ADMIN EXISTS ----------------
def admin_exists() -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
    exists = cursor.fetchone() is not None
    conn.close()
    return exists