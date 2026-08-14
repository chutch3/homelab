import os
import sqlite3
from backend.models import JobStatus, ChunkStatus


class Database:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def ensure_path_exists(self) -> None:
        db_dir = os.path.dirname(self._db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, timestamp TEXT, total_chunks INTEGER,
                status TEXT DEFAULT '{JobStatus.PENDING.value}', cookie TEXT, user_id TEXT, auth_user TEXT
            );
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, chunk_index INTEGER,
                status TEXT DEFAULT '{ChunkStatus.PENDING_DOWNLOAD.value}', message TEXT, FOREIGN KEY (job_id) REFERENCES jobs (id)
            );
        """)

        existing_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(chunks)").fetchall()}
        for column, ddl in [
            ("downloaded_bytes", "INTEGER DEFAULT 0"),
            ("total_bytes", "INTEGER"),
            ("speed_bytes_per_sec", "REAL"),
        ]:
            if column not in existing_columns:
                cursor.execute(f"ALTER TABLE chunks ADD COLUMN {column} {ddl}")

        conn.commit()
        conn.close()
