import sqlite3
import os
from datetime import datetime
from PyQt6.QtCore import QStandardPaths, QCoreApplication # QCoreApplication for app name/org if not already set

# Ensure an application instance exists for QStandardPaths if not run from main.py directly
# This is primarily for robustness if data_manager is used in a context where main.py hasn't set these.
# However, in our bundled app, main.py will always run first.
_app_instance_exists = QCoreApplication.instance() is not None
if not _app_instance_exists:
    # These must match main.py for consistency
    QCoreApplication.setOrganizationName("devdash AB")
    QCoreApplication.setApplicationName("Ergo")

# Define these constants, ensuring they match main.py if they are to be used by QStandardPaths indirectly
# For direct use in path construction, they are fine here.
ORGANIZATION_NAME = "devdash AB"
APPLICATION_NAME = "Ergo"

# Get the application data directory
# app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
# For Linux, AppDataLocation might be ~/.local/share/devdash AB/Ergo.
# Let's use AppConfigLocation which is often ~/.config/devdash AB/Ergo for config-like data,
# or GenericDataLocation for more general data. AppDataLocation is good.

app_data_dir_base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
if not app_data_dir_base: # Fallback if AppDataLocation is somehow not writable/available
    app_data_dir_base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
if not app_data_dir_base: # Further fallback to user's home directory
    app_data_dir_base = os.path.expanduser("~")
    # In this extreme fallback, create a hidden subdir to avoid cluttering home
    APP_DIR_IN_HOME = f".{APPLICATION_NAME.lower()}_data"
    final_app_data_path = os.path.join(app_data_dir_base, APP_DIR_IN_HOME, APPLICATION_NAME)
else:
    # Standard path construction
    final_app_data_path = os.path.join(app_data_dir_base, ORGANIZATION_NAME, APPLICATION_NAME)

# Ensure the directory exists
os.makedirs(final_app_data_path, exist_ok=True)

DB_PATH = os.path.join(final_app_data_path, 'posture_stats.db')
# print(f"[DEBUG data_manager] DB_PATH set to: {DB_PATH}") # For debugging

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