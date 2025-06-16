# tests/test_integration.py
import sqlite3, tempfile, os, threading
from app.processor import TaskProcessor
from app.utils import ExternalAPIClient, transform_data


def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    with open("app/schema.sql") as f:
        conn.executescript(f.read())
    return conn


def worker(db_path: str, wid: str):
    proc = TaskProcessor(db_path, ExternalAPIClient(), transform_data)
    tid = proc.claim_task(wid)
    if tid:
        assert proc.process_task(tid, wid) is True


def test_concurrent_processing():
    fd, db_path = tempfile.mkstemp()
    os.close(fd)

    conn = init_db(db_path)
    conn.execute("INSERT INTO tasks (status, raw_value) VALUES ('pending', 10)")
    conn.commit()
    conn.close()

    t1 = threading.Thread(target=worker, args=(db_path, "A"))
    t2 = threading.Thread(target=worker, args=(db_path, "B"))
    t1.start(); t2.start(); t1.join(); t2.join()

    with sqlite3.connect(db_path) as c:
        count = c.execute("SELECT COUNT(*) FROM tasks WHERE status='success'").fetchone()[0]
    assert count == 1
