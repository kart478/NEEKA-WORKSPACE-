from neeka.brain.exceptions import NEEKAError


class ArtifactError(NEEKAError):
    """Base artifact domain error."""


class ArtifactNotFoundError(ArtifactError):
    pass


class ArtifactPermissionError(ArtifactError):
    pass


class ArtifactValidationError(ArtifactError):
    pass


class ArtifactStorageError(ArtifactError):
    pass


class ArtifactStateError(ArtifactError):
    pass


class ArtifactIntegrityError(ArtifactError):
    pass
