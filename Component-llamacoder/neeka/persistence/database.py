import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 2


class Database:
    """Owns SQLite connections, schema initialization, and transactions."""

    def __init__(self, path: str | Path = "data/neeka.db") -> None:
        self.path = Path(path)
        self._memory_connection: sqlite3.Connection | None = None
        if str(self.path) == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:")
            self._memory_connection.row_factory = sqlite3.Row
            self._memory_connection.execute("PRAGMA foreign_keys = ON")
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        if self._memory_connection is not None:
            return self._memory_connection
        connection = sqlite3.connect(self.path if str(self.path) != ":memory:" else ":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if self._memory_connection is None:
                connection.close()

    def close(self) -> None:
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None

    def initialize(self) -> None:
        with self.session() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
            current = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if current is None:
                self._migration_v1(connection)
                connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
                self._migration_v2(connection)
            else:
                version = current["version"]
                if version < 2:
                    self._migration_v2(connection)
                    version = 2
                    connection.execute("UPDATE schema_version SET version = ?", (version,))
                if version < SCHEMA_VERSION:
                    connection.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))

    @staticmethod
    def _migration_v1(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL, active INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE projects (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, owner_id TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY(owner_id) REFERENCES users(id)
            );
            CREATE TABLE project_members (
                project_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL,
                joined_at TEXT NOT NULL, PRIMARY KEY(project_id, user_id),
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
                creator_id TEXT NOT NULL, assigned_to TEXT, status TEXT NOT NULL, priority TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, started_at TEXT, completed_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(creator_id) REFERENCES users(id), FOREIGN KEY(assigned_to) REFERENCES users(id)
            );
            CREATE TABLE task_dependencies (
                task_id TEXT NOT NULL, depends_on_id TEXT NOT NULL, PRIMARY KEY(task_id, depends_on_id),
                CHECK(task_id <> depends_on_id), FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY(depends_on_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, timestamp TEXT NOT NULL,
                actor_id TEXT, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, metadata TEXT NOT NULL,
                FOREIGN KEY(actor_id) REFERENCES users(id)
            );
            CREATE INDEX idx_events_timestamp ON events(timestamp);
            """
        )

    @staticmethod
    def _migration_v2(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS automation_executions (
                execution_id TEXT PRIMARY KEY, event_id TEXT NOT NULL, rule_id TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
                error TEXT, attempts INTEGER NOT NULL DEFAULT 1,
                UNIQUE(event_id, rule_id), FOREIGN KEY(event_id) REFERENCES events(event_id)
            );
            CREATE INDEX IF NOT EXISTS idx_automation_executions_status
                ON automation_executions(status);
            """
        )