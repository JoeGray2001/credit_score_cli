import sqlite3
import hashlib
import logging
from db import get_connection

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

def hash_password(password: str) -> str:
    logging.debug(f"Hashing password.")
    if not isinstance(password, str) or not password:
        logging.error("Password must be a non-empty string.")
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username: str, password: str, name: str = None, email: str = None) -> bool:
    logging.debug(f"Registering user: {username}")
    if not username or not password:
        logging.error("Username and password are required during registration.")
        raise ValueError("Username and password are required.")
    password_hash = hash_password(password)
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)",
                (username, password_hash, name, email)
            )
            conn.commit()
        logging.debug(f"User {username} registered successfully.")
        return True
    except sqlite3.IntegrityError:
        logging.error(f"User {username} registration failed: Username already exists.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error during registration: {e}")
        raise


def authenticate_user(username: str, password: str) -> bool:
    logging.debug(f"Authenticating user '{username}'.")
    password_hash = hash_password(password)
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
            result = c.fetchone()
        logging.debug(f"Authentication result for '{username}': {bool(result)}.")
        return result is not None
    except sqlite3.Error as e:
        logging.error(f"Database error during authenticate_user: {e}")
        raise

