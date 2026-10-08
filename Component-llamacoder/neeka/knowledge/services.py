from datetime import datetime
from typing import Callable

from .decision import Decision
from .document import Document, DocumentVersion
from .exceptions import KnowledgePermissionError
from .note import Note
from .project_knowledge import ProjectKnowledge
from .reference import Reference
from .repositories.base import KnowledgeRepository
from .requirement import Requirement


class KnowledgeService:
    def __init__(self, repository: KnowledgeRepository, can_access: Callable[[str, str], bool]) -> None:
        self.repository = repository
        self.can_access = can_access

    def _check(self, project_id: str, actor_id: str) -> None:
        if not self.can_access(project_id, actor_id):
            raise KnowledgePermissionError(f"Actor {actor_id} cannot access project {project_id} knowledge")

    def create_document(self, document: Document, actor_id: str) -> Document:
        self._check(document.project_id, actor_id)
        document.created_by = actor_id
        document.updated_at = datetime.utcnow()
        self.repository.save_document(document, DocumentVersion(document.id, 1, document.content, actor_id, metadata=document.metadata))
        return document

    def update_document(self, document_id: str, actor_id: str, **changes) -> Document:
        document = self.repository.get_document(document_id)
        if document is None:
            raise KeyError(document_id)
        self._check(document.project_id, actor_id)
        for key, value in changes.items():
            if value is not None and hasattr(document, key):
                setattr(document, key, value)
        document.version += 1
        document.updated_at = datetime.utcnow()
        self.repository.save_document(document, DocumentVersion(document.id, document.version, document.content, actor_id, metadata=document.metadata))
        return document

    def project(self, project_id: str, actor_id: str) -> ProjectKnowledge:
        self._check(project_id, actor_id)
        return self.repository.get_project_knowledge(project_id)

    def create_requirement(self, item: Requirement, actor_id: str) -> Requirement:
        self._check(item.project_id, actor_id)
        item.created_by = actor_id
        self.repository.save_requirement(item)
        return item

    def create_decision(self, item: Decision, actor_id: str) -> Decision:
        self._check(item.project_id, actor_id)
        item.created_by = actor_id
        self.repository.save_decision(item)
        return item

    def update_decision(self, decision_id: str, actor_id: str, **changes) -> Decision:
        decisions = self.repository.list_decisions(changes.pop("project_id", "")) if "project_id" in changes else []
        item = next((decision for decision in decisions if decision.id == decision_id), None)
        if item is None:
            raise KeyError(decision_id)
        self._check(item.project_id, actor_id)
        for key, value in changes.items():
            if value is not None and hasattr(item, key):
                setattr(item, key, value)
        item.updated_at = datetime.utcnow()
        self.repository.save_decision(item)
        return item

    def add_relationship(self, project_id: str, actor_id: str, source_type: str, source_id: str,
                         relationship: str, target_type: str, target_id: str) -> None:
        self._check(project_id, actor_id)
        self.repository.add_relationship(source_type, source_id, relationship, target_type, target_id)

    def create_note(self, item: Note, actor_id: str) -> Note:
        self._check(item.project_id, actor_id)
        item.author = actor_id
        self.repository.save_note(item)
        return item

    def create_reference(self, item: Reference, actor_id: str) -> Reference:
        self._check(item.project_id, actor_id)
        item.created_by = actor_id
        self.repository.save_reference(item)
        return item
