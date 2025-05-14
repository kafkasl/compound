import apsw
import datetime as dt
from pathlib import Path
import os


# Determine database path based on environment
if os.environ.get("PLASH_PRODUCTION") == "1":
    # Production path in /app directory
    db_path = Path("db/habits_production.db")
else:
    # Development path
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
    habit_units = []  # Add this to store units
    all_data = []
    count_data = []
    
    # Get data for each habit
    for habit in habits:
        habit_id = habit["id"]
        habit_name = habit["name"]
        habit_unit = habit["unit"] or ""  # Get unit (or empty string if None)
        
        habit_names.append(habit_name)
        habit_units.append(habit_unit)
        
        # Query entries for this habit in date range - get BOTH sum and count
        cur = conn.cursor()
        sums = cur.execute("""
            SELECT date, SUM(value) 
            FROM entries 
            WHERE habit_id = ? AND date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
        """, (habit_id, start_date.isoformat(), end_date.isoformat())).fetchall()
        
        counts = cur.execute("""
            SELECT date, COUNT(*) 
            FROM entries 
            WHERE habit_id = ? AND date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
        """, (habit_id, start_date.isoformat(), end_date.isoformat())).fetchall()
        
        # Convert to dicts for easier lookup
        sum_dict = dict(sums)
        count_dict = dict(counts)
        
        # Create rows of values for this habit (one per date)
        sum_row = [sum_dict.get(date, 0) for date in date_strs]
        count_row = [count_dict.get(date, 0) for date in date_strs]
        
        all_data.append(sum_row)
        count_data.append(count_row)
    
    return {
        "habits": habit_names,
        "units": habit_units,
        "dates": date_range,
        "data": all_data,
        "counts": count_data
    }

def get_habits_with_counts():
    today = dt.date.today().isoformat()
    habits = get_habits()
    
    # Add today's counts to each habit
    for habit in habits:
        habit_id = habit["id"]
        # Query for today's total and count
        cur = conn.cursor()
        
        # Get total volume
        total_result = cur.execute("""
            SELECT SUM(value) 
            FROM entries 
            WHERE habit_id = ? AND date = ?
        """, (habit_id, today)).fetchone()
        
        # Get count of entries
        count_result = cur.execute("""
            SELECT COUNT(*) 
            FROM entries 
            WHERE habit_id = ? AND date = ?
        """, (habit_id, today)).fetchone()
        
        # Add values to the habit data
        today_total = total_result[0] if total_result[0] is not None else 0
        today_count = count_result[0] if count_result[0] is not None else 0
        
        habit["today_total"] = today_total
        habit["today_count"] = today_count
    
    return habits

def delete_last_entry(habit_id):
    """Delete the most recent entry for a habit"""
    cur = conn.cursor()
    
    # Find the latest entry ID for this habit
    entry = cur.execute("""
        SELECT id FROM entries 
        WHERE habit_id = ? 
        ORDER BY timestamp DESC LIMIT 1
    """, (habit_id,)).fetchone()
    
    if not entry:
        return False
    
    # Delete the entry
    cur.execute("DELETE FROM entries WHERE id = ?", (entry[0],))
    return True