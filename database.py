import os
import sqlite3

def get_db_path(db_path=None):
    """
    Get the database file path from parameter or environment variable.
    """
    if db_path:
        return db_path
    return os.environ.get("DATABASE_NAME", "auth_system.db")

def get_db_connection(db_path=None):
    """
    Establish and return a connection to the SQLite database.
    Row factory is set to sqlite3.Row for convenient column access by name.
    """
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """
    Automatically create the SQLite database and users table if they do not exist.
    Stores:
      - id (INTEGER PRIMARY KEY)
      - name (TEXT)
      - email (TEXT UNIQUE)
      - password (TEXT - hashed bcrypt string)
      - created_at (TIMESTAMP)
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def create_user(name, email, hashed_password, db_path=None):
    """
    Insert a new user record into the database.
    Returns the newly created user's ID on success, or None if insertion fails.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        # Handles duplicate email or other constraint violations
        return None
    finally:
        conn.close()

def get_user_by_email(email, db_path=None):
    """
    Fetch a user by email address (case-insensitive).
    Returns sqlite3.Row or None.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email.strip().lower(),))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id, db_path=None):
    """
    Fetch a user by their unique primary key ID.
    Returns sqlite3.Row or None.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
