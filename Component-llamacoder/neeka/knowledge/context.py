from dataclasses import asdict
from typing import Any

from .project_knowledge import ProjectKnowledge


class KnowledgeContextBuilder:
    """Produces bounded structured context for the Intelligence Layer."""

    def build(self, knowledge: ProjectKnowledge) -> dict[str, Any]:
        return asdict(knowledge)
