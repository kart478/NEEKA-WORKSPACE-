from dataclasses import dataclass
from enum import Enum


class ArtifactRole(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    REFERENCE = "REFERENCE"
    ATTACHMENT = "ATTACHMENT"


@dataclass(frozen=True)
class ArtifactRelationship:
    artifact_id: str
    target_type: str
    target_id: str
    role: ArtifactRole
