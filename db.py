import apsw
import datetime as dt
from pathlib import Path
import os
from fastmigrate.core import create_db, run_migrations
from fastcore.all import dict2obj

import apsw.bestpractice

apsw.bestpractice.apply(apsw.bestpractice.recommended)

# Determine database path based on environment
if os.environ.get("PLASH_PRODUCTION") == "1": db_path = Path("data/habits-prod.db")
else: db_path = Path("data/habits.db")

db_path.parent.mkdir(parents=True, exist_ok=True)    
migrations_dir = "migrations"

# Init DB
# Create/verify there is a versioned database, or else fail
current_version = create_db(db_path)
print(f"DB: {current_version=}")

success = run_migrations(db_path, migrations_dir, verbose=False)
if not success: raise Exception("Database migration failed!")


conn= apsw.Connection(str(db_path))

def ensure_user(user_id, email, name, picture):
    cur = conn.cursor()
    print(f"Ensuring user {user_id} {email} {name} {picture}")
    cur.execute("INSERT OR IGNORE INTO users (id, email, name, picture) VALUES (?, ?, ?, ?)",
                (user_id, email, name, picture))
    return cur.getconnection().last_insert_rowid()

def get_user(user_id):
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, picture FROM users WHERE id = ?", (user_id,))
    id, email, name, picture = cur.fetchone()
    return dict2obj({"id": id, "email": email, "name": name, "picture": picture})

# Core operations
def add_habit(user_id, name, unit=None, default_value=1.0):
    cur = conn.cursor()
    cur.execute("INSERT INTO habits (user_id, name, unit, default_value) VALUES (?, ?, ?, ?)", 
                (user_id, name, unit, default_value))
    return cur.getconnection().last_insert_rowid()

def record_habit(user_id, habit_id, value=None):
    cur = conn.cursor()
    # Verify the habit belongs to the user
    habit = cur.execute("SELECT default_value FROM habits WHERE id = ? AND user_id = ?", 
                        (habit_id, user_id)).fetchone()
    
    if not habit: return None  # Habit not found or doesn't belong to user
    if value is None: value = habit[0] # use default value if not provided
        
    today = dt.date.today().isoformat()
    timestamp = int(dt.datetime.now().timestamp())
    cur.execute("INSERT INTO entries (habit_id, value, date, timestamp) VALUES (?, ?, ?, ?)",
                (habit_id, value, today, timestamp))
    return cur.getconnection().last_insert_rowid()

def get_habits(user_id):
    return [{"id": id, "name": name, "unit": unit, "default_value": default_value}
            for id, name, unit, default_value in 
            conn.cursor().execute("SELECT id, name, unit, default_value FROM habits WHERE user_id = ?", 
                                 (user_id,))]

def get_habit_stats(habit_id, user_id, start_date, end_date):
    """Get sum and count statistics for a habit in a date range"""
    cur = conn.cursor()
    results = cur.execute("""
        SELECT date, SUM(value) as total, COUNT(*) as count
        FROM entries e
        JOIN habits h ON e.habit_id = h.id
        WHERE e.habit_id = ? AND h.user_id = ? AND date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date
    """, (habit_id, user_id, start_date.isoformat(), end_date.isoformat())).fetchall()
    
    # Convert to dicts for easier lookup
    sum_dict = {date: total for date, total, _ in results}
    count_dict = {date: count for date, _, count in results}
    
    return sum_dict, count_dict

def get_heatmap_data(user_id):
    # Get all habits for this user
    habits = get_habits(user_id)
    
    # Determine date range (last 30 days by default)
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=30)
    date_range = [start_date + dt.timedelta(days=x) for x in range(31)]
    date_strs = [d.isoformat() for d in date_range]
    
    # Initialize data
    habit_names = []
    habit_units = []
    all_data = []
    count_data = []
    
    # Get data for each habit
    for habit in habits:
        habit_names.append(habit["name"])
        habit_units.append(habit.get("unit", ""))
        
        # Get stats for this habit in the date range
        sum_dict, count_dict = get_habit_stats(habit["id"], user_id, start_date, end_date)
        
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

def get_habits_with_counts(user_id):
    today = dt.date.today()
    habits = get_habits(user_id)
    
    # Add today's counts and latest entry value to each habit
    for habit in habits:
        sum_dict, count_dict = get_habit_stats(habit["id"], user_id, today, today)
        
        # Get latest entry value for this habit
        cur = conn.cursor()
        latest_entry = cur.execute("""
            SELECT value FROM entries e
            JOIN habits h ON e.habit_id = h.id
            WHERE e.habit_id = ? AND h.user_id = ?
            ORDER BY e.timestamp DESC LIMIT 1
        """, (habit["id"], user_id)).fetchone()
        
        # Add values to the habit data (using today's date as key)
        today_str = today.isoformat()
        habit["today_total"] = sum_dict.get(today_str, 0)
        habit["today_count"] = count_dict.get(today_str, 0)
        habit["latest_value"] = latest_entry[0] if latest_entry else habit["default_value"]
    
    return habits

def delete_last_entry(user_id, habit_id):
    """Delete the most recent entry for a habit"""
    cur = conn.cursor()
    
    # Delete the latest entry in a single statement
    cur.execute("""
        DELETE FROM entries WHERE id IN (
            SELECT id FROM (
                SELECT e.id FROM entries e
                JOIN habits h ON e.habit_id = h.id
                WHERE e.habit_id = ? AND h.user_id = ?
                ORDER BY e.timestamp DESC LIMIT 1
            )
        )
    """, (habit_id, user_id))
    
    # Return true if any row was deleted
    changes = conn.changes()
    return changes > 0

def delete_habit(user_id, habit_id):
    """Delete a habit and all its entries"""
    cur = conn.cursor()
    
    # Delete the habit (with user_id check for security)
    # Entries will be deleted automatically via ON DELETE CASCADE
    cur.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", 
                               (habit_id, user_id))
    changes = conn.changes()
    return changes > 0