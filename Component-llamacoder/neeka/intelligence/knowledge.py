from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ProjectDocumentation:
    project_id: str
    title: str
    content: str
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ProjectDecision:
    project_id: str
    title: str
    decision: str
    decided_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ProjectReference:
    project_id: str
    title: str
    uri: str


@dataclass(frozen=True)
class ProjectKnowledge:
    documentation: list[ProjectDocumentation] = field(default_factory=list)
    decisions: list[ProjectDecision] = field(default_factory=list)
    references: list[ProjectReference] = field(default_factory=list)