from collections.abc import Callable

from .exceptions import ArtifactPermissionError


class ArtifactPermissions:
    def __init__(self, can_access: Callable[[str, str], bool]) -> None:
        self.can_access = can_access

    def check(self, project_id: str, actor_id: str) -> None:
        if not self.can_access(project_id, actor_id):
            raise ArtifactPermissionError(f"Actor {actor_id} cannot access project {project_id} artifacts")
