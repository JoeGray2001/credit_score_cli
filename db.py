import sqlite3
from pathlib import Path

DB_PATH = Path("credit_score.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

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
