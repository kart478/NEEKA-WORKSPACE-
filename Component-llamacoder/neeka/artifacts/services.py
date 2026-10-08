from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePath
from typing import BinaryIO, Callable

from .artifact import Artifact, ArtifactStatus, ArtifactType
from .exceptions import ArtifactNotFoundError, ArtifactStateError, ArtifactValidationError
from .metadata import build_metadata
from .permissions import ArtifactPermissions
from .relationships import ArtifactRelationship, ArtifactRole
from .repositories.base import ArtifactRepository
from .storage import ArtifactStorage
from .version import ArtifactVersion

_SAFE_NAME = re.compile(r"^[^\\/:*?\"<>|\x00-\x1f]+$")


class ArtifactService:
    def __init__(self, repository: ArtifactRepository, storage: ArtifactStorage,
                 can_access: Callable[[str, str], bool], max_size: int = 50 * 1024 * 1024) -> None:
        self.repository = repository
        self.storage = storage
        self.permissions = ArtifactPermissions(can_access)
        self.max_size = max_size

    def _check_name(self, name: str) -> None:
        if not name or len(name) > 255 or not _SAFE_NAME.fullmatch(name) or PurePath(name).name != name:
            raise ArtifactValidationError("Unsafe artifact filename")

    def create(self, project_id: str, name: str, description: str, artifact_type: ArtifactType,
               mime_type: str, source: BinaryIO, actor_id: str, metadata: dict | None = None) -> Artifact:
        self.permissions.check(project_id, actor_id)
        self._check_name(name)
        artifact_id = __import__("uuid").uuid4().hex
        key = f"{project_id}/{artifact_id}/versions/1/{name}"
        size, checksum = self.storage.save(key, source, self.max_size)
        artifact = Artifact(project_id, name, description, artifact_type, mime_type, size, key, checksum, actor_id,
                            metadata=build_metadata(name, mime_type, size, checksum, metadata), id=artifact_id)
        version = ArtifactVersion(artifact.id, 1, key, size, checksum, actor_id)
        try:
            self.repository.save(artifact, version)
        except Exception:
            self.storage.delete(key)
            raise
        return artifact

    def get(self, artifact_id: str, actor_id: str) -> Artifact:
        artifact = self.repository.get(artifact_id)
        if artifact is None:
            raise ArtifactNotFoundError(f"Artifact {artifact_id} not found")
        self.permissions.check(artifact.project_id, actor_id)
        return artifact

    def list(self, project_id: str, actor_id: str) -> list[Artifact]:
        self.permissions.check(project_id, actor_id)
        return self.repository.list(project_id)

    def add_version(self, artifact_id: str, source: BinaryIO, actor_id: str, metadata: dict | None = None) -> Artifact:
        artifact = self.get(artifact_id, actor_id)
        if artifact.status in (ArtifactStatus.DELETED, ArtifactStatus.ARCHIVED):
            raise ArtifactStateError(f"Cannot version artifact in {artifact.status.value} state")
        number = artifact.current_version + 1
        key = f"{artifact.project_id}/{artifact.id}/versions/{number}/{artifact.name}"
        size, checksum = self.storage.save(key, source, self.max_size)
        version = ArtifactVersion(artifact.id, number, key, size, checksum, actor_id)
        artifact.current_version = number
        artifact.storage_key = key
        artifact.size = size
        artifact.checksum = checksum
        artifact.updated_at = datetime.utcnow()
        artifact.metadata = build_metadata(artifact.name, artifact.mime_type, size, checksum, metadata or artifact.metadata)
        try:
            self.repository.save(artifact, version)
        except Exception:
            self.storage.delete(key)
            raise
        return artifact

    def versions(self, artifact_id: str, actor_id: str) -> list[ArtifactVersion]:
        self.get(artifact_id, actor_id)
        return self.repository.versions(artifact_id)

    def restore_version(self, artifact_id: str, version_number: int, actor_id: str) -> Artifact:
        artifact = self.get(artifact_id, actor_id)
        version = next((item for item in self.repository.versions(artifact_id)
                        if item.version_number == version_number), None)
        if version is None:
            raise ArtifactValidationError(f"Artifact version {version_number} not found")
        if hasattr(self.storage, "verify"):
            self.storage.verify(version.storage_key, version.checksum)
        artifact.storage_key = version.storage_key
        artifact.size = version.size
        artifact.checksum = version.checksum
        artifact.current_version = version.version_number
        artifact.status = ArtifactStatus.AVAILABLE
        artifact.updated_at = datetime.utcnow()
        self.repository.save(artifact, version)
        return artifact

    def read(self, artifact_id: str, actor_id: str):
        artifact = self.get(artifact_id, actor_id)
        if artifact.status == ArtifactStatus.DELETED:
            raise ArtifactStateError("Deleted artifacts cannot be downloaded")
        if hasattr(self.storage, "verify"):
            self.storage.verify(artifact.storage_key, artifact.checksum)
        return self.storage.read(artifact.storage_key)

    def remove(self, artifact_id: str, actor_id: str) -> Artifact:
        artifact = self.get(artifact_id, actor_id)
        if artifact.status == ArtifactStatus.DELETED:
            return artifact
        artifact.status = ArtifactStatus.DELETED
        artifact.updated_at = datetime.utcnow()
        self.repository.save(artifact, self.repository.versions(artifact.id)[-1])
        return artifact

    def attach(self, artifact_id: str, target_type: str, target_id: str, role: ArtifactRole, actor_id: str) -> ArtifactRelationship:
        artifact = self.get(artifact_id, actor_id)
        relationship = ArtifactRelationship(artifact.id, target_type, target_id, role)
        self.repository.add_relationship(relationship)
        return relationship

    def relationships(self, artifact_id: str, actor_id: str) -> list[ArtifactRelationship]:
        self.get(artifact_id, actor_id)
        return self.repository.relationships(artifact_id)

    def detach(self, artifact_id: str, target_type: str, target_id: str, role: ArtifactRole, actor_id: str) -> None:
        self.get(artifact_id, actor_id)
        self.repository.remove_relationship(ArtifactRelationship(artifact_id, target_type, target_id, role))

    def duplicates(self, project_id: str, checksum: str, actor_id: str) -> list[Artifact]:
        self.permissions.check(project_id, actor_id)
        return self.repository.find_checksum(project_id, checksum)

    def extract_text(self, artifact_id: str, actor_id: str) -> str:
        self.get(artifact_id, actor_id)
        raise ArtifactValidationError("Artifact text extraction is not implemented")

    def extract_metadata(self, artifact_id: str, actor_id: str) -> dict:
        artifact = self.get(artifact_id, actor_id)
        return dict(artifact.metadata)

    def analyze_artifact(self, artifact_id: str, actor_id: str) -> dict:
        artifact = self.get(artifact_id, actor_id)
        return {"artifact_id": artifact.id, "status": "NOT_IMPLEMENTED", "artifact_type": artifact.artifact_type.value}

    def for_target(self, target_type: str, target_id: str, project_id: str, actor_id: str) -> list[Artifact]:
        self.permissions.check(project_id, actor_id)
        return self.repository.artifacts_for_target(target_type, target_id)
