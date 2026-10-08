from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from uuid import uuid4

from neeka.persistence.database import Database
from ..decision import Decision, DecisionStatus
from ..document import Document, DocumentStatus, DocumentType, DocumentVersion
from ..note import Note
from ..project_knowledge import ProjectKnowledge
from ..reference import Reference
from ..requirement import Requirement, RequirementPriority, RequirementStatus


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SQLiteKnowledgeRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save_document(self, document: Document, version: DocumentVersion) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO documents
                (id, project_id, title, description, content, document_type, status, created_by,
                 created_at, updated_at, version, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, description=excluded.description,
                 content=excluded.content, document_type=excluded.document_type, status=excluded.status,
                 updated_at=excluded.updated_at, version=excluded.version, metadata=excluded.metadata""",
                (document.id, document.project_id, document.title, document.description, document.content,
                 document.document_type.value, document.status.value, document.created_by,
                 document.created_at.isoformat(), document.updated_at.isoformat(), document.version,
                 json.dumps(document.metadata)),
            )
            connection.execute(
                """INSERT INTO document_versions
                (id, document_id, version, content, created_by, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(document_id, version) DO NOTHING""",
                (version.id, version.document_id, version.version, version.content, version.created_by,
                 version.created_at.isoformat(), json.dumps(version.metadata)),
            )

    def get_document(self, document_id: str) -> Document | None:
        with self.database.session() as connection:
            row = connection.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._document(row) if row else None

    def list_documents(self, project_id: str) -> list[Document]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM documents WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
        return [self._document(row) for row in rows]

    def list_document_versions(self, document_id: str) -> list[DocumentVersion]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM document_versions WHERE document_id = ? ORDER BY version", (document_id,)).fetchall()
        return [DocumentVersion(row["document_id"], row["version"], row["content"], row["created_by"], _date(row["created_at"]), json.loads(row["metadata"]), row["id"]) for row in rows]

    def save_requirement(self, item: Requirement) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO requirements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, description=excluded.description,
                priority=excluded.priority, status=excluded.status, source=excluded.source, updated_at=excluded.updated_at""",
                (item.id, item.project_id, item.title, item.description, item.priority.value, item.status.value,
                 item.source, item.created_by, item.created_at.isoformat(), item.updated_at.isoformat()),
            )

    def list_requirements(self, project_id: str) -> list[Requirement]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM requirements WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
        return [Requirement(row["project_id"], row["title"], row["description"], row["created_by"], RequirementPriority(row["priority"]), RequirementStatus(row["status"]), row["source"], row["id"], _date(row["created_at"]), _date(row["updated_at"])) for row in rows]

    def save_decision(self, item: Decision) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, decision=excluded.decision,
                reason=excluded.reason, alternatives_considered=excluded.alternatives_considered,
                status=excluded.status, superseded_by=excluded.superseded_by, updated_at=excluded.updated_at""",
                (item.id, item.project_id, item.title, item.decision, item.reason, json.dumps(item.alternatives_considered),
                 item.status.value, item.superseded_by, item.created_by, item.created_at.isoformat(), item.updated_at.isoformat()),
            )

    def list_decisions(self, project_id: str) -> list[Decision]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM decisions WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
        return [Decision(row["project_id"], row["title"], row["decision"], row["reason"], row["created_by"], json.loads(row["alternatives_considered"]), DecisionStatus(row["status"]), row["superseded_by"], row["id"], _date(row["created_at"]), _date(row["updated_at"])) for row in rows]

    def save_note(self, item: Note) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, content=excluded.content,
                updated_at=excluded.updated_at""",
                (item.id, item.project_id, item.title, item.content, item.author, item.created_at.isoformat(), item.updated_at.isoformat()),
            )
            self._save_tags(connection, "note", item.id, item.tags)

    def list_notes(self, project_id: str) -> list[Note]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM notes WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
        return [Note(row["project_id"], row["title"], row["content"], row["author"], self.tags("note", row["id"]), row["id"], _date(row["created_at"]), _date(row["updated_at"])) for row in rows]

    def save_reference(self, item: Reference) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO "references" VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, url=excluded.url,
                description=excluded.description, source_type=excluded.source_type""",
                (item.id, item.project_id, item.title, item.url, item.description, item.source_type, item.created_by, item.created_at.isoformat()),
            )

    def list_references(self, project_id: str) -> list[Reference]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM \"references\" WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
        return [Reference(row["project_id"], row["title"], row["url"], row["description"], row["source_type"], row["created_by"], row["id"], _date(row["created_at"])) for row in rows]

    def get_project_knowledge(self, project_id: str) -> ProjectKnowledge:
        return ProjectKnowledge(project_id, self.list_documents(project_id), self.list_requirements(project_id), self.list_decisions(project_id), self.list_notes(project_id), self.list_references(project_id))

    def _save_tags(self, connection: sqlite3.Connection, entity_type: str, entity_id: str, names: list[str]) -> None:
        connection.execute("DELETE FROM entity_tags WHERE entity_type = ? AND entity_id = ?", (entity_type, entity_id))
        for name in names:
            tag_id = str(uuid4())
            connection.execute("INSERT INTO tags(id, name) VALUES (?, ?) ON CONFLICT(name) DO NOTHING", (tag_id, name))
            row = connection.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
            connection.execute("INSERT OR IGNORE INTO entity_tags VALUES (?, ?, ?)", (entity_type, entity_id, row["id"]))

    def tags(self, entity_type: str, entity_id: str) -> list[str]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT tags.name FROM tags JOIN entity_tags ON tags.id = entity_tags.tag_id WHERE entity_type = ? AND entity_id = ? ORDER BY tags.name", (entity_type, entity_id)).fetchall()
        return [row["name"] for row in rows]

    def search(self, project_id: str, keyword: str, type: str | None = None, status: str | None = None) -> list[dict]:
        pattern = f"%{keyword}%"
        queries = {
            "document": ("documents", "id, title, description, content, document_type AS type, status", "title LIKE ? OR description LIKE ? OR content LIKE ?"),
            "requirement": ("requirements", "id, title, description, 'REQUIREMENT' AS type, status", "title LIKE ? OR description LIKE ? OR source LIKE ?"),
            "decision": ("decisions", "id, title, decision AS description, 'DECISION' AS type, status", "title LIKE ? OR decision LIKE ? OR reason LIKE ?"),
            "note": ("notes", "id, title, content AS description, 'NOTE' AS type, '' AS status", "title LIKE ? OR content LIKE ?"),
            "reference": ("\"references\"", "id, title, description, 'REFERENCE' AS type, '' AS status", "title LIKE ? OR description LIKE ? OR url LIKE ?"),
        }
        kinds = [type.lower()] if type and type.lower() in queries else list(queries)
        results: list[dict] = []
        with self.database.session() as connection:
            for kind in kinds:
                table, columns, condition = queries[kind]
                args = [project_id, pattern, pattern] + ([pattern] if condition.count("?") == 3 else [])
                sql = f"SELECT {columns} FROM {table} WHERE project_id = ? AND ({condition})"
                if status:
                    sql += " AND status = ?"
                    args.append(status)
                rows = connection.execute(sql, args).fetchall()
                results.extend([{**dict(row), "type": kind.upper()} for row in rows])
        return results

    def add_relationship(self, source_type: str, source_id: str, relationship: str, target_type: str, target_id: str) -> None:
        with self.database.session() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO knowledge_relationships VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid4()), source_type, source_id, relationship, target_type, target_id),
            )

    def relationships(self, source_type: str, source_id: str) -> list[dict]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT source_type, source_id, relationship, target_type, target_id FROM knowledge_relationships WHERE source_type = ? AND source_id = ?",
                (source_type, source_id),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _document(row: sqlite3.Row) -> Document:
        return Document(row["project_id"], row["title"], row["description"], row["content"], DocumentType(row["document_type"]), DocumentStatus(row["status"]), row["created_by"], row["id"], _date(row["created_at"]), _date(row["updated_at"]), row["version"], json.loads(row["metadata"]))
