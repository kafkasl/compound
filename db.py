import apsw
import datetime as dt
from pathlib import Path
import plotly.express as px
import pandas as pd
import json

# Create db directory if it doesn't exist
db_path = Path("db/habits.db")
db_path.parent.mkdir(parents=True, exist_ok=True)
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


def get_heatmap_data():
    # Get all habits
    habits = get_habits()
    
    # Determine date range (last 30 days by default)
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=30)
    date_range = [start_date + dt.timedelta(days=x) for x in range(31)]
    date_strs = [d.isoformat() for d in date_range]
    
    # Initialize data
    habit_names = []
    all_data = []
    
    # Get data for each habit
    for habit in habits:
        habit_id = habit["id"]
        habit_name = habit["name"]
        habit_names.append(habit_name)
        
        # Query entries for this habit in date range
        cur = conn.cursor()
        entries = cur.execute("""
            SELECT date, SUM(value) 
            FROM entries 
            WHERE habit_id = ? AND date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
        """, (habit_id, start_date.isoformat(), end_date.isoformat())).fetchall()
        
        # Convert to dict for easier lookup
        data_dict = dict(entries)
        
        # Create row of values for this habit (one per date)
        row_data = [data_dict.get(date, 0) for date in date_strs]
        all_data.append(row_data)
    
    return {
        "habits": habit_names,
        "dates": date_range,
        "data": all_data
    }