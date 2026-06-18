# services/auth_service.py

from database.db import get_connection, return_connection
import hashlib

# ---------------- HASH PASSWORD ----------------
def hash_password(password: str) -> str:
    """Return a SHA-256 hash of the password."""
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------- CREATE USER ----------------
def create_user(username: str, password: str, role: str = "user") -> bool:
    """Create a new user in PostgreSQL. Returns True if successful, False if username exists."""
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
        conn.rollback()
        print(f"Create user error: {e}")
        return False
    finally:
        return_connection(conn)


# ---------------- LOGIN USER ----------------
def login_user(username: str, password: str):
    """Return user dict if credentials are correct, else None."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id, username, role, password FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()
        
        if row and row[3] == hash_password(password):
            return {"id": row[0], "username": row[1], "role": row[2]}
        return None
    finally:
        return_connection(conn)


# ---------------- CHECK ADMIN EXISTS ----------------
def admin_exists() -> bool:
    """Return True if an admin user exists."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
        return cursor.fetchone() is not None
    finally:
        return_connection(conn)


# ===================== NEW FUNCTION =====================
def count_admins() -> int:
    """Return the total number of admin users in the system."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        count = cursor.fetchone()[0]
        return count
    finally:
        return_connection(conn)
# ========================================================


# ---------------- GET ALL USERS ----------------
def get_all_users():
    """Get all users (for admin management)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [{"id": r[0], "username": r[1], "role": r[2], "created_at": r[3]} for r in rows]
    finally:
        return_connection(conn)


# ---------------- UPDATE USER ROLE ----------------
def update_user_role(user_id: int, new_role: str) -> bool:
    """Update a user's role."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating user role: {e}")
        return False
    finally:
        return_connection(conn)


# ---------------- DELETE USER ----------------
def delete_user(user_id: int) -> bool:
    """Delete a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error deleting user: {e}")
        return False
    finally:
        return_connection(conn)


# ---------------- CHANGE PASSWORD ----------------
def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change user's password."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verify old password
        cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        
        if not row or row[0] != hash_password(old_password):
            return False
        
        # Update to new password
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hash_password(new_password), user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error changing password: {e}")
        return False
    finally:
        return_connection(conn)