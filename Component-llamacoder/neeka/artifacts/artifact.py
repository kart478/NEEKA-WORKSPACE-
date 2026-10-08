from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class ArtifactType(str, Enum):
    DOCUMENT = "DOCUMENT"
    SPREADSHEET = "SPREADSHEET"
    PRESENTATION = "PRESENTATION"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    ARCHIVE = "ARCHIVE"
    CODE = "CODE"
    DATA = "DATA"
    OTHER = "OTHER"


class ArtifactStatus(str, Enum):
    PENDING = "PENDING"
    AVAILABLE = "AVAILABLE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"
    FAILED = "FAILED"


@dataclass
class Artifact:
    project_id: str
    name: str
    description: str
    artifact_type: ArtifactType
    mime_type: str
    size: int
    storage_key: str
    checksum: str
    created_by: str
    status: ArtifactStatus = ArtifactStatus.AVAILABLE
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    current_version: int = 1
