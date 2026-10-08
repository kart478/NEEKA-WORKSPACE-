from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class ArtifactVersion:
    artifact_id: str
    version_number: int
    storage_key: str
    size: int
    checksum: str
    created_by: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
