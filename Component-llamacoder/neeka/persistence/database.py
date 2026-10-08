import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 4


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
                self._migration_v3(connection)
                self._migration_v4(connection)
            else:
                version = current["version"]
                if version < 2:
                    self._migration_v2(connection)
                    version = 2
                if version < 3:
                    self._migration_v3(connection)
                    version = 3
                if version < 4:
                    self._migration_v4(connection)
                    version = 4
                connection.execute("UPDATE schema_version SET version = ?", (version,))

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

    @staticmethod
    def _migration_v3(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ai_audit_records (
                audit_id TEXT PRIMARY KEY, provider TEXT NOT NULL, operation TEXT NOT NULL,
                action TEXT, parameters TEXT NOT NULL, permission_mode TEXT NOT NULL,
                timestamp TEXT NOT NULL, success INTEGER NOT NULL, error TEXT,
                project_id TEXT, task_id TEXT, execution_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ai_audit_timestamp ON ai_audit_records(timestamp);
            """
        )

    @staticmethod
    def _migration_v4(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT NOT NULL, content TEXT NOT NULL, document_type TEXT NOT NULL,
                status TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, version INTEGER NOT NULL, metadata TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS document_versions (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, version INTEGER NOT NULL,
                content TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
                metadata TEXT NOT NULL, UNIQUE(document_id, version),
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS requirements (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL,
                source TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
                decision TEXT NOT NULL, reason TEXT NOT NULL, alternatives_considered TEXT NOT NULL,
                status TEXT NOT NULL, superseded_by TEXT, created_by TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id), FOREIGN KEY(superseded_by) REFERENCES decisions(id)
            );
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
                content TEXT NOT NULL, author TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(author) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS "references" (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
                url TEXT NOT NULL, description TEXT NOT NULL, source_type TEXT NOT NULL,
                created_by TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS tags (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
            CREATE TABLE IF NOT EXISTS entity_tags (
                entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, tag_id TEXT NOT NULL,
                PRIMARY KEY(entity_type, entity_id, tag_id), FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS knowledge_relationships (
                id TEXT PRIMARY KEY, source_type TEXT NOT NULL, source_id TEXT NOT NULL,
                relationship TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL,
                UNIQUE(source_type, source_id, relationship, target_type, target_id)
            );
            CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
            CREATE INDEX IF NOT EXISTS idx_requirements_project ON requirements(project_id);
            CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);
            CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_id);
            CREATE INDEX IF NOT EXISTS idx_references_project ON "references"(project_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_relationship_source ON knowledge_relationships(source_type, source_id);
            """
        )