from __future__ import annotations

import sqlite3

from backend.db.database import Database


class TestDatabaseMigration:
    def test_adds_missing_columns_to_a_preexisting_table(self, tmp_path) -> None:
        """Simulates a live deployment's DB file predating a new column: create the
        table with the old (shorter) column set by hand, then confirm Database's
        table creation grows it to match the current model, in place."""
        db_file = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute(
            """
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, timestamp TEXT, total_chunks INTEGER,
                status TEXT DEFAULT 'pending', cookie TEXT, user_id TEXT, auth_user TEXT
            )
            """
        )
        conn.commit()
        conn.close()

        Database(url=f"sqlite:///{db_file}")

        conn = sqlite3.connect(str(db_file))
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        conn.close()
        assert "metadata_status" in columns

    def test_preserves_existing_rows_when_adding_a_column(self, tmp_path) -> None:
        db_file = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute(
            """
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, timestamp TEXT, total_chunks INTEGER,
                status TEXT DEFAULT 'pending', cookie TEXT, user_id TEXT, auth_user TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO jobs (job_id, timestamp, total_chunks, status, cookie, user_id, auth_user) "
            "VALUES ('abc', 't', 1, 'in_progress', 'c', 'u', '0')"
        )
        conn.commit()
        conn.close()

        Database(url=f"sqlite:///{db_file}")

        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM jobs WHERE job_id = 'abc'").fetchone()
        conn.close()
        assert row["status"] == "in_progress"
        assert row["metadata_status"] is None
