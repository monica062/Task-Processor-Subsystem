--schema.sql
-- Tabel tasks
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    locked_by TEXT,
    raw_value INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indeks untuk performa query concurrency control
CREATE INDEX IF NOT EXISTS idx_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_locked_by ON tasks(locked_by);

-- Tabel audit_log
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL,
    response_code INTEGER,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);