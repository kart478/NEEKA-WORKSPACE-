from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from neeka.persistence.database import Database
from ..artifact import Artifact, ArtifactStatus, ArtifactType
from ..relationships import ArtifactRelationship, ArtifactRole
from ..version import ArtifactVersion


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SQLiteArtifactRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, artifact: Artifact, version: ArtifactVersion) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO artifacts
                (id, project_id, name, description, artifact_type, mime_type, size, storage_key,
                 checksum, created_by, created_at, updated_at, status, metadata, current_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET description=excluded.description,
                 artifact_type=excluded.artifact_type, mime_type=excluded.mime_type, size=excluded.size,
                 storage_key=excluded.storage_key, checksum=excluded.checksum, updated_at=excluded.updated_at,
                 status=excluded.status, metadata=excluded.metadata, current_version=excluded.current_version""",
                (artifact.id, artifact.project_id, artifact.name, artifact.description, artifact.artifact_type.value,
                 artifact.mime_type, artifact.size, artifact.storage_key, artifact.checksum, artifact.created_by,
                 artifact.created_at.isoformat(), artifact.updated_at.isoformat(), artifact.status.value,
                 json.dumps(artifact.metadata), artifact.current_version),
            )
            connection.execute(
                """INSERT INTO artifact_versions
                (id, artifact_id, version_number, storage_key, size, checksum, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(artifact_id, version_number) DO NOTHING""",
                (version.id, version.artifact_id, version.version_number, version.storage_key, version.size,
                 version.checksum, version.created_by, version.created_at.isoformat()),
            )

    def get(self, artifact_id: str) -> Artifact | None:
        with self.database.session() as connection:
            row = connection.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        return self._map(row) if row else None

    def list(self, project_id: str) -> list[Artifact]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM artifacts WHERE project_id = ? AND status <> 'DELETED' ORDER BY created_at", (project_id,)).fetchall()
        return [self._map(row) for row in rows]

    def versions(self, artifact_id: str) -> list[ArtifactVersion]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM artifact_versions WHERE artifact_id = ? ORDER BY version_number", (artifact_id,)).fetchall()
        return [ArtifactVersion(row["artifact_id"], row["version_number"], row["storage_key"], row["size"], row["checksum"], row["created_by"], row["id"], _date(row["created_at"])) for row in rows]

    def find_checksum(self, project_id: str, checksum: str) -> list[Artifact]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM artifacts WHERE project_id = ? AND checksum = ? AND status <> 'DELETED'", (project_id, checksum)).fetchall()
        return [self._map(row) for row in rows]

    def delete(self, artifact_id: str, updated_at: str) -> None:
        with self.database.session() as connection:
            connection.execute("UPDATE artifacts SET status = 'DELETED', updated_at = ? WHERE id = ?", (updated_at, artifact_id))

    def add_relationship(self, relationship: ArtifactRelationship) -> None:
        with self.database.session() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO artifact_relationships(artifact_id, target_type, target_id, role) VALUES (?, ?, ?, ?)",
                (relationship.artifact_id, relationship.target_type, relationship.target_id, relationship.role.value),
            )

    def relationships(self, artifact_id: str) -> list[ArtifactRelationship]:
        with self.database.session() as connection:
            rows = connection.execute("SELECT * FROM artifact_relationships WHERE artifact_id = ?", (artifact_id,)).fetchall()
        return [ArtifactRelationship(row["artifact_id"], row["target_type"], row["target_id"], ArtifactRole(row["role"])) for row in rows]

    def remove_relationship(self, relationship: ArtifactRelationship) -> None:
        with self.database.session() as connection:
            connection.execute(
                "DELETE FROM artifact_relationships WHERE artifact_id = ? AND target_type = ? AND target_id = ? AND role = ?",
                (relationship.artifact_id, relationship.target_type, relationship.target_id, relationship.role.value),
            )

    def artifacts_for_target(self, target_type: str, target_id: str) -> list[Artifact]:
        with self.database.session() as connection:
            rows = connection.execute(
                """SELECT artifacts.* FROM artifacts JOIN artifact_relationships
                   ON artifacts.id = artifact_relationships.artifact_id
                   WHERE artifact_relationships.target_type = ? AND artifact_relationships.target_id = ?
                   AND artifacts.status <> 'DELETED' ORDER BY artifacts.created_at""",
                (target_type, target_id),
            ).fetchall()
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: sqlite3.Row) -> Artifact:
        return Artifact(row["project_id"], row["name"], row["description"], ArtifactType(row["artifact_type"]),
                        row["mime_type"], row["size"], row["storage_key"], row["checksum"], row["created_by"],
                        ArtifactStatus(row["status"]), json.loads(row["metadata"]), row["id"],
                        _date(row["created_at"]), _date(row["updated_at"]), row["current_version"])
