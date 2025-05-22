-- Add habits and entries tables with user references

-- Create the habits table with user_id
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY, 
    user_id TEXT NOT NULL,
    name TEXT NOT NULL, 
    unit TEXT, 
    default_value REAL DEFAULT 1.0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create the entries table
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY, 
    habit_id INTEGER, 
    value REAL NOT NULL, 
    date TEXT NOT NULL, 
    timestamp INTEGER,
    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
); 