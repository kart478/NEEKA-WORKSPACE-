from datetime import datetime
from uuid import uuid4

from neeka.persistence.repositories import AIAuditRepository


class AIAuditor:
    def __init__(self, repository: AIAuditRepository) -> None:
        self.repository = repository

    def record(self, provider: str, operation: str, permission_mode: str, success: bool,
               action: str | None = None, parameters: dict | None = None, error: str | None = None,
               project_id: str | None = None, task_id: str | None = None,
               execution_id: str | None = None) -> dict:
        record = {
            "audit_id": str(uuid4()), "provider": provider, "operation": operation,
            "action": action, "parameters": parameters or {}, "permission_mode": permission_mode,
            "timestamp": datetime.utcnow().isoformat(), "success": success, "error": error,
            "project_id": project_id, "task_id": task_id, "execution_id": execution_id,
        }
        self.repository.append(record)
        return record

    def list(self) -> list[dict]:
        return self.repository.list()