from dataclasses import dataclass, field
from typing import Any

from .decision import Decision
from .document import Document
from .note import Note
from .reference import Reference
from .requirement import Requirement


@dataclass
class ProjectKnowledge:
    project_id: str
    documents: list[Document] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "documents": self.documents,
            "requirements": self.requirements,
            "decisions": self.decisions,
            "notes": self.notes,
            "references": self.references,
        }
