from database.db import get_connection, return_connection
import hashlib
import os

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
        print(f"Create user error: {e}")
        conn.rollback()
        return False
    finally:
        return_connection(conn)

# ---------------- LOGIN USER (FIXED - uses tuple indexing) ----------------
def login_user(username: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, username, role, password FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()  # Returns a TUPLE, not dictionary
        
        if row:
            # Access by index: (id, username, role, password)
            user_id = row[0]
            user_username = row[1]
            user_role = row[2]
            user_password = row[3]
            
            if user_password == hash_password(password):
                return {
                    "id": user_id,
                    "username": user_username,
                    "role": user_role
                }
        return None
    except Exception as e:
        print(f"Login error: {e}")
        raise e
    finally:
        return_connection(conn)

# ---------------- CHECK ADMIN EXISTS ----------------
def admin_exists() -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
        row = cursor.fetchone()
        return row is not None
    except Exception as e:
        print(f"Admin exists check error: {e}")
        return False
    finally:
        return_connection(conn)

# ---------------- GET USER BY ID ----------------
def get_user_by_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, username, role, created_at FROM users WHERE id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "created_at": row[3]
            }
        return None
    finally:
        return_connection(conn)

# ---------------- GET ALL USERS ----------------
def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "created_at": row[3]
            })
        return users
    finally:
        return_connection(conn)

# ---------------- UPDATE USER ROLE ----------------
def update_user_role(user_id: int, new_role: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET role = %s WHERE id = %s RETURNING id, username, role",
            (new_role, user_id)
        )
        row = cursor.fetchone()
        conn.commit()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "role": row[2]
            }
        return None
    except Exception as e:
        conn.rollback()
        print(f"Update role error: {e}")
        raise e
    finally:
        return_connection(conn)

# ---------------- DELETE USER ----------------
def delete_user(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
        row = cursor.fetchone()
        conn.commit()
        return row is not None
    except Exception as e:
        conn.rollback()
        print(f"Delete user error: {e}")
        return False
    finally:
        return_connection(conn)

# ---------------- CHANGE PASSWORD ----------------
def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # First verify old password
        old_hashed = hash_password(old_password)
        cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        
        if not row or row[0] != old_hashed:
            return False
        
        # Update to new password
        new_hashed = hash_password(new_password)
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_hashed, user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Change password error: {e}")
        return False
    finally:
        return_connection(conn)

# ---------------- CREATE DEFAULT ADMIN ----------------
def create_default_admin():
    """Create default admin user if no users exist"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if any users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("No users found. Creating default admin user...")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
            hashed = hash_password(admin_password)
            
            cursor.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, %s)
            """, ("admin", hashed, "admin"))
            
            conn.commit()
            print(f"Default admin user created. Username: admin, Password: {admin_password}")
            return True
        return False
    except Exception as e:
        print(f"Error creating default admin: {e}")
        conn.rollback()
        return False
    finally:
        return_connection(conn)