"""
database.py
-----------
Handles all SQLite operations for the Hospital Analyzer app.
Uses a simple class-based approach for clean code structure.
"""

import sqlite3
import pandas as pd
import os

# Path to the SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "hospital.db")


class Database:
    """Handles all database read/write operations."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        # Make sure the folder exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        """Returns a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # lets us access columns by name
        return conn

    def _init_db(self):
        """Creates tables if they don't already exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Main OPD records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opd_records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                time        TEXT NOT NULL,
                department  TEXT NOT NULL,
                wait_time   REAL NOT NULL,
                outcome     TEXT NOT NULL,
                hour        INTEGER,
                day_of_week TEXT,
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table to track each upload session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT,
                row_count   INTEGER,
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def clear_records(self):
        """Deletes all existing OPD records (fresh upload)."""
        conn = self._get_connection()
        conn.execute("DELETE FROM opd_records")
        conn.commit()
        conn.close()

    def insert_dataframe(self, df, filename="unknown"):
        """
        Inserts a cleaned pandas DataFrame into the database.
        Also logs the upload session.
        """
        conn = self._get_connection()

        # Save OPD records
        df.to_sql("opd_records", conn, if_exists="replace", index=False)

        # Log the upload
        conn.execute(
            "INSERT INTO upload_sessions (filename, row_count) VALUES (?, ?)",
            (filename, len(df))
        )
        conn.commit()
        conn.close()

    def get_all_records(self):
        """Fetches all OPD records as a pandas DataFrame."""
        conn = self._get_connection()
        df = pd.read_sql("SELECT * FROM opd_records", conn)
        conn.close()
        return df

    def get_summary_stats(self):
        """Returns basic stats: total rows, departments, date range."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM opd_records")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(DISTINCT department) as depts FROM opd_records")
        depts = cursor.fetchone()["depts"]

        cursor.execute("SELECT MIN(date) as start_date, MAX(date) as end_date FROM opd_records")
        row = cursor.fetchone()
        conn.close()

        return {
            "total_records": total,
            "departments": depts,
            "start_date": row["start_date"],
            "end_date": row["end_date"]
        }

    def has_data(self):
        """Returns True if there is at least one record in the DB."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM opd_records")
        count = cursor.fetchone()["cnt"]
        conn.close()
        return count > 0
