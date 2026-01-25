import os
import sqlite3
from backend.models import JobStatus, ChunkStatus


class Database:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self.ensure_path_exists()
        self.create_tables()

    def ensure_path_exists(self):
        db_dir = os.path.dirname(self._db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def get_connection(self):
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self):
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
        conn.commit()
        conn.close()
