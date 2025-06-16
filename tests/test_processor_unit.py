#test/test_processor_unit.py
import sqlite3
from unittest.mock import MagicMock, patch
import pytest
from app.processor import TaskProcessor
from app.utils import transform_data, ExternalAPIClient


def make_db(tmp_path):
    db_path = tmp_path / "unit.db"
    conn = sqlite3.connect(db_path)
    with open("app/schema.sql", "r") as f:
        conn.executescript(f.read())
    return db_path, conn


def test_claim_task_success(tmp_path):
    db_path, conn = make_db(tmp_path)
    conn.execute("INSERT INTO tasks (status, raw_value) VALUES ('pending', 10)")
    conn.commit()

    processor = TaskProcessor(str(db_path), MagicMock(), transform_data)
    task_id = processor.claim_task("worker-1")

    assert task_id is not None
    status = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()[0]
    assert status == "in_progress"


def test_process_task_success(tmp_path):
    db_path, conn = make_db(tmp_path)
    conn.execute("INSERT INTO tasks (status, raw_value) VALUES ('pending', 10)")
    conn.commit()

    mock_api = MagicMock()
    mock_api.send.return_value.status_code = 200

    processor = TaskProcessor(str(db_path), mock_api, transform_data)
    task_id = processor.claim_task("w1")
    ok = processor.process_task(task_id, "w1")

    assert ok is True
    status = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()[0]
    assert status == "success"


@patch("sqlite3.connect")
def test_process_task_failure_on_transient_error(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"id": 1, "status": "pending", "raw_value": 10},
        {"id": 1, "status": "in_progress", "raw_value": 10}
    ]
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    mock_api = MagicMock()
    mock_api.send.side_effect = [
        type('obj', (object,), {'status_code': 500}),
        type('obj', (object,), {'status_code': 500}),
        type('obj', (object,), {'status_code': 200})
    ]

    processor = TaskProcessor(":memory:", mock_api, transform_data, max_retries=2)

    task_id = processor.claim_task("worker-1")
    success = processor.process_task(task_id, "worker-1")

    assert success is True
    mock_cursor.execute.assert_any_call("UPDATE tasks SET status='success' WHERE id=1")


def test_process_task_transform_failure(tmp_path):
    db_path, conn = make_db(tmp_path)
    conn.execute("INSERT INTO tasks (status, raw_value) VALUES ('pending', 10)")
    conn.commit()

    mock_api = MagicMock()
    mock_api.send.return_value.status_code = 200

    processor = TaskProcessor(str(db_path), mock_api, lambda x: 1 / 0)

    task_id = processor.claim_task("worker-1")
    success = processor.process_task(task_id, "worker-1")

    assert success is False
    
    