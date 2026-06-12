import sqlite3
import hashlib
import os
from database.db import get_connection, return_connection

# ---------- Ensure database folder exists ----------
DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "auth.db")  # Separate auth DB

# ---------------- INIT DATABASE ----------------
def init_auth_db():
    """Create users table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


# ---------------- HASH PASSWORD ----------------
def hash_password(password: str) -> str:
    """Return a SHA-256 hash of the password."""
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------- CREATE USER ----------------
def create_user(username: str, password: str, role: str = "user") -> bool:
    """Create a new user. Returns True if successful, False if username exists."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ---------------- LOGIN USER ----------------
def login_user(username: str, password: str):
    """Return user dict if credentials are correct, else None."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, role, password FROM users WHERE username=?",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()

    if user and user[3] == hash_password(password):
        return {"id": user[0], "username": user[1], "role": user[2]}
    return None


# ---------------- CHECK ADMIN EXISTS ----------------
def admin_exists() -> bool:
    """Return True if an admin user exists."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1")
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


# ---------------- GET ALL USERS ----------------
def get_all_users():
    """Get all users (for admin management)."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [{"id": r[0], "username": r[1], "role": r[2], "created_at": r[3]} for r in rows]


# ---------------- UPDATE USER ROLE ----------------
def update_user_role(user_id: int, new_role: str) -> bool:
    """Update a user's role."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user role: {e}")
        return False
    finally:
        conn.close()


# ---------------- DELETE USER ----------------
def delete_user(user_id: int) -> bool:
    """Delete a user."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        conn.close()


# ---------------- CHANGE PASSWORD ----------------
def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change user's password."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verify old password
        cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row or row[0] != hash_password(old_password):
            return False
        
        # Update to new password
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_password), user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error changing password: {e}")
        return False
    finally:
        conn.close()


# ---------------- CREATE DEFAULT ADMIN IF NO USERS EXIST ----------------
def create_default_admin_if_needed():
    """Create default admin only if no users exist at all."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if any users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("No users found. Creating default admin user...")
            default_password = "admin123"
            hashed = hash_password(default_password)
            
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", hashed, "admin")
            )
            conn.commit()
            print(f"Default admin user created. Username: admin, Password: {default_password}")
            print("IMPORTANT: Please change the default password after first login!")
            return True
        return False
    except Exception as e:
        print(f"Error creating default admin: {e}")
        return False
    finally:
        conn.close()