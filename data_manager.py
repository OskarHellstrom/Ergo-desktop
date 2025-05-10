import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'posture_stats.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_date TEXT NOT NULL,
            reminder_count INTEGER NOT NULL
        )
    ''')
    # No primary key needed here if we are summing, but adding one is generally good practice.
    # For now, let's keep it as is to ensure Option 3 works without schema migration issues.
    # If we wanted to enforce one session entry per day and update, we'd add:
    # c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_session_date ON sessions (session_date);')
    conn.commit()
    conn.close()

def add_session_data(date_str, count):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # This will insert a new row for each session completed.
    # The aggregation will happen in get_session_data.
    c.execute('INSERT INTO sessions (session_date, reminder_count) VALUES (?, ?)', (date_str, count))
    conn.commit()
    conn.close()

def get_session_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Sum reminder_counts for each date, group by date, and order by date
    c.execute('SELECT session_date, SUM(reminder_count) FROM sessions GROUP BY session_date ORDER BY session_date ASC')
    rows = c.fetchall()
    conn.close()
    # Filter out days with zero total reminders, as they don't make sense on the graph
    filtered_rows = [row for row in rows if row[1] > 0]
    return filtered_rows 