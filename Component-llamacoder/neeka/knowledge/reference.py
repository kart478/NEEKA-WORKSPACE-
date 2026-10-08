from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Reference:
    project_id: str
    title: str
    url: str
    description: str
    source_type: str
    created_by: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
