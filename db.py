import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

DB_PATH = Path("credit_score.db")

def get_connection():
    try: 
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        raise

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                email TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS credit_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                age INTEGER,
                income REAL,
                debts REAL,
                missed_payments INTEGER,
                employment_length_years INTEGER,
                credit_history_years INTEGER,
                credit_score INTEGER,
                last_updated DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
