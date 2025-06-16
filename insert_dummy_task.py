#insert_dummy_task.py
import sqlite3

conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# Hapus task lama jika ada
cursor.execute("DELETE FROM tasks WHERE id = 1")

# Masukkan task dummy
cursor.execute("""
    INSERT INTO tasks (id, status, raw_value) VALUES (?, ?, ?)
""", (1, 'pending', 10))  # raw_value = 10

conn.commit()
conn.close()
print("Dummy task berhasil ditambahkan.")