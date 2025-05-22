-- Initial schema migration with user support

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT,
    picture TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
); 