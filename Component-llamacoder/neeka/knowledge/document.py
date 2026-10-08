from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class DocumentType(str, Enum):
    SPECIFICATION = "SPECIFICATION"
    REQUIREMENT_DOCUMENT = "REQUIREMENT_DOCUMENT"
    ARCHITECTURE = "ARCHITECTURE"
    MEETING_NOTES = "MEETING_NOTES"
    REPORT = "REPORT"
    GUIDE = "GUIDE"
    REFERENCE = "REFERENCE"
    OTHER = "OTHER"


class DocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


@dataclass
class DocumentVersion:
    document_id: str
    version: int
    content: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class Document:
    project_id: str
    title: str
    description: str
    content: str
    document_type: DocumentType = DocumentType.OTHER
    status: DocumentStatus = DocumentStatus.DRAFT
    created_by: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
