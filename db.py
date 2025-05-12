import apsw
import datetime as dt
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import io

db_path = Path("habits.db")
conn = apsw.Connection(str(db_path))

# Init DB
def init_db():
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY, 
        name TEXT NOT NULL, 
        unit TEXT, 
        default_value REAL DEFAULT 1.0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY, 
        habit_id INTEGER, 
        value REAL NOT NULL, 
        date TEXT NOT NULL, 
        timestamp INTEGER,
        FOREIGN KEY (habit_id) REFERENCES habits(id))''')

# Core operations
def add_habit(name, unit=None, default_value=1.0):
    cur = conn.cursor()
    cur.execute("INSERT INTO habits (name, unit, default_value) VALUES (?, ?, ?)", 
                (name, unit, default_value))
    return cur.getconnection().last_insert_rowid()

def record_habit(habit_id, value=None):
    cur = conn.cursor()
    if value is None:
        value = cur.execute("SELECT default_value FROM habits WHERE id = ?", 
                           (habit_id,)).fetchone()[0]
    today = dt.date.today().isoformat()
    timestamp = int(dt.datetime.now().timestamp())
    cur.execute("INSERT INTO entries (habit_id, value, date, timestamp) VALUES (?, ?, ?, ?)",
                (habit_id, value, today, timestamp))
    return cur.getconnection().last_insert_rowid()

def get_habits():
    return [{"id": id, "name": name, "unit": unit, "default_value": default_value}
            for id, name, unit, default_value in 
            conn.cursor().execute("SELECT id, name, unit, default_value FROM habits")]

def get_heatmap_data(habit_id):
    cur = conn.cursor()
    entries = cur.execute("""
        SELECT date, SUM(value) FROM entries 
        WHERE habit_id = ? GROUP BY date
        ORDER BY date""", (habit_id,)).fetchall()
    return dict(entries)

# Visualization
def generate_heatmap(habit_id):
    habit = conn.cursor().execute("SELECT name, unit FROM habits WHERE id = ?", 
                                 (habit_id,)).fetchone()
    data = get_heatmap_data(habit_id)
    
    # Create calendar heatmap (simple version)
    dates = list(data.keys())
    values = list(data.values())
    
    plt.figure(figsize=(10, 2))
    plt.bar(dates, values, color='green')
    plt.title(f"{habit[0]} ({habit[1] or 'count'})")
    plt.tight_layout()
    
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close()
    
    return img_bytes

