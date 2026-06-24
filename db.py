import sqlite3
from contextlib import contextmanager

DB_PATH = "coach.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS seller_context (
                id INTEGER PRIMARY KEY,
                product TEXT NOT NULL,
                icp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY,
                prospect_name TEXT,
                prospect_role TEXT,
                prospect_company TEXT,
                channel TEXT DEFAULT 'email',
                thread_text TEXT NOT NULL,
                failure_mode TEXT,
                failure_confidence INTEGER,
                failure_explanation TEXT,
                recovery_draft TEXT,
                pattern_tags TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
