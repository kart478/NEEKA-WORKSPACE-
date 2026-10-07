from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from uuid import uuid4

from neeka.brain.event import Event, EventType
from neeka.brain.project import Project, ProjectStatus
from neeka.brain.task import Task, TaskPriority, TaskStatus
from neeka.brain.user import User, UserRole
from .database import Database


def _date(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _required_date(value: str) -> datetime:
    parsed = _date(value)
    if parsed is None:
        raise ValueError("A required timestamp was empty")
    return parsed


class SQLiteUserRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, user: User) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO users(id, name, email, role, active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, email=excluded.email,
                   role=excluded.role, active=excluded.active, updated_at=excluded.updated_at""",
                (user.id, user.name, user.email, user.role.value, int(user.active),
                 user.created_at.isoformat(), user.updated_at.isoformat()),
            )

    def get(self, user_id: str) -> User | None:
        with self.database.session() as connection:
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._map(row) if row else None

    def list(self) -> list[User]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM users ORDER BY created_at").fetchall()
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: sqlite3.Row) -> User:
        return User(row["name"], row["email"], UserRole(row["role"]), bool(row["active"]),
                    row["id"], _required_date(row["created_at"]), _required_date(row["updated_at"]))


class SQLiteProjectRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, project: Project) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO projects(id, name, description, owner_id, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description,
                   owner_id=excluded.owner_id, status=excluded.status, updated_at=excluded.updated_at""",
                (project.id, project.name, project.description, project.owner_id, project.status.value,
                 project.created_at.isoformat(), project.updated_at.isoformat()),
            )
            for member_id in project.member_ids:
                connection.execute(
                    "INSERT OR IGNORE INTO project_members(project_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
                    (project.id, member_id, "MEMBER", project.created_at.isoformat()),
                )

    def get(self, project_id: str) -> Project | None:
        with self.database.session() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                return None
            members = connection.execute(
                """SELECT user_id FROM project_members WHERE project_id = ?
                   ORDER BY CASE WHEN user_id = ? THEN 0 ELSE 1 END, joined_at, rowid""",
                (project_id, row["owner_id"]),
            ).fetchall()
            tasks = connection.execute(
                "SELECT id FROM tasks WHERE project_id = ? ORDER BY created_at", (project_id,)
            ).fetchall()
        return Project(row["name"], row["description"], row["owner_id"], ProjectStatus(row["status"]),
                       row["id"], _required_date(row["created_at"]), _required_date(row["updated_at"]),
                       [item["user_id"] for item in members], [item["id"] for item in tasks])

    def list(self) -> list[Project]:
        with self.database.session() as connection:
            ids = [row["id"] for row in connection.execute("SELECT id FROM projects ORDER BY created_at")]
        return [project for project_id in ids if (project := self.get(project_id)) is not None]

    def add_member(self, project_id: str, user_id: str, role: str = "MEMBER") -> None:
        with self.database.session() as connection:
            connection.execute(
                "INSERT INTO project_members(project_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
                (project_id, user_id, role, datetime.utcnow().isoformat()),
            )

    def has_member(self, project_id: str, user_id: str) -> bool:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, user_id)
            ).fetchone()
        return row is not None

    def remove_member(self, project_id: str, user_id: str) -> None:
        with self.database.session() as connection:
            connection.execute(
                "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
                (project_id, user_id),
            )

    def delete(self, project_id: str) -> None:
        with self.database.session() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))


class SQLiteTaskRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, task: Task) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO tasks(id, project_id, title, description, creator_id, assigned_to, status, priority,
                   created_at, updated_at, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET assigned_to=excluded.assigned_to, status=excluded.status,
                   priority=excluded.priority, updated_at=excluded.updated_at, started_at=excluded.started_at,
                   completed_at=excluded.completed_at, title=excluded.title, description=excluded.description""",
                (task.id, task.project_id, task.title, task.description, task.creator_id, task.assigned_to,
                 task.status.value, task.priority.value, task.created_at.isoformat(), task.updated_at.isoformat(),
                 task.started_at.isoformat() if task.started_at else None,
                 task.completed_at.isoformat() if task.completed_at else None),
            )

    def get(self, task_id: str) -> Task | None:
        with self.database.session() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                return None
            dependencies = connection.execute(
                "SELECT depends_on_id FROM task_dependencies WHERE task_id = ?", (task_id,)
            ).fetchall()
        return self._map(row, [item["depends_on_id"] for item in dependencies])

    def list(self) -> list[Task]:
        with self.database.session() as connection:
            ids = [row["id"] for row in connection.execute("SELECT id FROM tasks ORDER BY created_at")]
        return [task for task_id in ids if (task := self.get(task_id)) is not None]

    def add_dependency(self, task_id: str, depends_on_id: str) -> None:
        with self.database.session() as connection:
            connection.execute(
                "INSERT INTO task_dependencies(task_id, depends_on_id) VALUES (?, ?)", (task_id, depends_on_id)
            )

    def remove_dependency(self, task_id: str, depends_on_id: str) -> None:
        with self.database.session() as connection:
            connection.execute(
                "DELETE FROM task_dependencies WHERE task_id = ? AND depends_on_id = ?",
                (task_id, depends_on_id),
            )

    @staticmethod
    def _map(row: sqlite3.Row, dependencies: list[str]) -> Task:
        return Task(row["title"], row["description"], row["project_id"], row["creator_id"],
                    TaskPriority(row["priority"]), TaskStatus(row["status"]), row["id"],
                    _required_date(row["created_at"]), _required_date(row["updated_at"]),
                    _date(row["started_at"]), _date(row["completed_at"]), row["assigned_to"], dependencies)


class SQLiteEventRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def append(self, event: Event) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO events(event_id, event_type, timestamp, actor_id, entity_type, entity_id, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event.id, event.event_type.value, event.timestamp.isoformat(), event.actor_id,
                 "task" if event.event_type.value.startswith("TASK") else "project",
                 event.source_entity, json.dumps(event.metadata)),
            )

    def list(self) -> list[Event]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM events ORDER BY timestamp, event_id").fetchall()
        return [Event(EventType(row["event_type"]), row["entity_id"], row["actor_id"],
                      json.loads(row["metadata"]), row["event_id"], _required_date(row["timestamp"]))
                for row in rows]


class SQLiteAutomationExecutionRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def start(self, event_id: str, rule_id: str) -> str | None:
        execution_id = str(uuid4())
        with self.database.session() as connection:
            try:
                connection.execute(
                    """INSERT INTO automation_executions
                       (execution_id, event_id, rule_id, status, started_at)
                       VALUES (?, ?, ?, 'RUNNING', ?)""",
                    (execution_id, event_id, rule_id, datetime.utcnow().isoformat()),
                )
            except sqlite3.IntegrityError:
                return None
        return execution_id

    def finish(self, execution_id: str, status: str, error: str | None = None) -> None:
        with self.database.session() as connection:
            connection.execute(
                """UPDATE automation_executions SET status = ?, finished_at = ?, error = ?
                   WHERE execution_id = ?""",
                (status, datetime.utcnow().isoformat(), error, execution_id),
            )

    def retry(self, event_id: str, rule_id: str) -> str | None:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT execution_id, attempts FROM automation_executions WHERE event_id = ? AND rule_id = ?",
                (event_id, rule_id),
            ).fetchone()
            if not row:
                return self.start(event_id, rule_id)
            execution_id = row["execution_id"]
            connection.execute(
                """UPDATE automation_executions SET status = 'RUNNING', finished_at = NULL,
                   error = NULL, attempts = attempts + 1 WHERE execution_id = ?""",
                (execution_id,),
            )
        return execution_id

    def list(self) -> list[dict]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT * FROM automation_executions ORDER BY started_at, execution_id"
            ).fetchall()
        return [dict(row) for row in rows]


class SQLiteAIAuditRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def append(self, record: dict) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO ai_audit_records
                   (audit_id, provider, operation, action, parameters, permission_mode,
                    timestamp, success, error, project_id, task_id, execution_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record["audit_id"], record["provider"], record["operation"], record.get("action"),
                 json.dumps(record.get("parameters", {})), record["permission_mode"],
                 record["timestamp"], int(record["success"]), record.get("error"),
                 record.get("project_id"), record.get("task_id"), record.get("execution_id")),
            )

    def list(self) -> list[dict]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM ai_audit_records ORDER BY timestamp, audit_id").fetchall()
        return [
            {**dict(row), "parameters": json.loads(row["parameters"]), "success": bool(row["success"])}
            for row in rows
        ]