#init_db.py
import sqlite3

conn = sqlite3.connect('tasks.db')
with open('app/schema.sql', 'r') as f:
    conn.executescript(f.read())
conn.close()
print("Database berhasil dibuat.")