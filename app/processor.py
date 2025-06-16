# app/processor.py
import sqlite3
import threading
from typing import Any, Dict

from app.utils import retry_with_backoff


# --------------------------------------------------------------------- #
#  Koneksi bersama untuk ':memory:' supaya bisa dipakai di beberapa
#  thread dalam pengujian (integration test memakai file, jadi aman).
# --------------------------------------------------------------------- #
_MEM_CONN_LOCK = threading.Lock()
_SHARED_MEM_URI = "file:sharedmem?mode=memory&cache=shared"


def _open_connection(db_path: str) -> sqlite3.Connection:
    """Buka koneksi SQLite.  Untuk ':memory:' gunakan shared‑cache."""
    if db_path == ":memory:":
        with _MEM_CONN_LOCK:
            conn = sqlite3.connect(_SHARED_MEM_URI, uri=True, check_same_thread=False)
        return conn
    return sqlite3.connect(db_path)


# --------------------------------------------------------------------- #
#  TaskProcessor
# --------------------------------------------------------------------- #
class TaskProcessor:
    def __init__(self, db_path: str, api_client, transform_func, max_retries: int = 3):
        self.db_path = db_path
        self.api_client = api_client
        self.transform = transform_func
        self.max_retries = max_retries

    # --------------------------- claim_task --------------------------- #
    def claim_task(self, worker_id: str) -> Any | None:
        conn = _open_connection(self.db_path)
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE tasks
            SET status='in_progress', locked_by=?
            WHERE id = (
                SELECT id FROM tasks
                WHERE status='pending' AND locked_by IS NULL
                LIMIT 1
            )
            """,
            (worker_id,),
        )
        conn.commit()

        cur.execute("SELECT id FROM tasks WHERE locked_by=?", (worker_id,))
        row = cur.fetchone()
        # Row mungkin tuple (DB asli) atau dict (mock)
        if not row:
            return None
        return row[0] if not isinstance(row, dict) else row.get("id")

    # ---------------------------- log_audit --------------------------- #
    @staticmethod
    def _log_audit(
        cur: sqlite3.Cursor,
        task_id: int,
        attempt: int,
        event: str,
        code: int | None = None,
        msg: str | None = None,
    ) -> None:
        """Simpan audit—kolom mengikuti schema.sql."""
        cur.execute(
            """
            INSERT INTO audit_log
            (task_id, attempt_number, event_type, response_code, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, attempt, event, code, msg),
        )

    # --------------------------- process_task ------------------------- #
    def process_task(self, task_id: int, worker_id: str) -> bool:
        """
        • Ambil task → transform → kirim ke API dgn retry
        • Perbarui status + audit.
        • Return True jika sukses.
        """
        attempt = 0  # dihitung ulang oleh retry_with_backoff

        # Gunakan koneksi yang sama sepanjang fungsi agar transaksi konsisten.
        conn = _open_connection(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            # === Fetch task detail ===
            self._log_audit(cur, task_id, attempt, "fetch")

            cur.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
            row = cur.fetchone()
            if not row:
                self._log_audit(cur, task_id, attempt, "failure", msg="Task not found")
                conn.commit()
                return False

            task_dict: Dict[str, Any] = dict(row)

            # === Transform ===
            try:
                transformed = self.transform(task_dict)
            except Exception as exc:
                self._log_audit(cur, task_id, attempt, "failure", msg=str(exc))
                cur.execute(f"UPDATE tasks SET status='failed' WHERE id={task_id}")
                conn.commit()
                return False

            # === Kirim API dengan retry ===
            def _send():
                nonlocal attempt
                resp = self.api_client.send(transformed)
                attempt += 1
                return resp

            resp = retry_with_backoff(_send, self.max_retries)

            # === Update status & audit ===
            if resp and 200 <= resp.status_code < 300:
                cur.execute(f"UPDATE tasks SET status='success' WHERE id={task_id}")
                self._log_audit(cur, task_id, attempt, "success", code=resp.status_code)
                conn.commit()
                return True
            else:
                cur.execute(f"UPDATE tasks SET status='failed' WHERE id={task_id}")
                self._log_audit(
                    cur,
                    task_id,
                    attempt,
                    "failure",
                    code=resp.status_code if resp else None,
                )
                conn.commit()
                return False

        except Exception as exc:  # fallback untuk error tak terduga
            self._log_audit(cur, task_id, attempt, "failure", msg=str(exc))
            cur.execute(f"UPDATE tasks SET status='failed' WHERE id={task_id}")
            conn.commit()
            return False
