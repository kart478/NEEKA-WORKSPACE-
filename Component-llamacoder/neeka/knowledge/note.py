from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Note:
    project_id: str
    title: str
    content: str
    author: str
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
