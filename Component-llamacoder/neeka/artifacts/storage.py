from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from .exceptions import ArtifactIntegrityError, ArtifactStorageError, ArtifactValidationError


class ArtifactStorage:
    def save(self, storage_key: str, source: BinaryIO, max_size: int) -> tuple[int, str]: ...
    def read(self, storage_key: str) -> BinaryIO: ...
    def delete(self, storage_key: str) -> None: ...
    def exists(self, storage_key: str) -> bool: ...
    def get_metadata(self, storage_key: str) -> dict: ...


class LocalArtifactStorage:
    def __init__(self, root: str | Path, chunk_size: int = 1024 * 1024) -> None:
        self.root = Path(root).resolve()
        self.chunk_size = chunk_size
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, storage_key: str) -> Path:
        key = PurePosixPath(storage_key)
        if (key.is_absolute() or "\\" in storage_key or ":" in storage_key
                or any(part in ("", ".", "..") for part in key.parts)):
            raise ArtifactValidationError("Unsafe artifact storage key")
        path = (self.root / Path(*key.parts)).resolve()
        if path != self.root and self.root not in path.parents:
            raise ArtifactValidationError("Artifact storage key escapes storage root")
        return path

    def save(self, storage_key: str, source: BinaryIO, max_size: int) -> tuple[int, str]:
        destination = self._path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".uploading")
        size = 0
        digest = hashlib.sha256()
        try:
            with temporary.open("wb") as output:
                while chunk := source.read(self.chunk_size):
                    size += len(chunk)
                    if size > max_size:
                        raise ArtifactValidationError("Artifact exceeds the configured size limit")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(destination)
            return size, digest.hexdigest()
        except Exception as error:
            temporary.unlink(missing_ok=True)
            if isinstance(error, ArtifactValidationError):
                raise
            raise ArtifactStorageError("Unable to store artifact") from error

    def read(self, storage_key: str) -> BinaryIO:
        path = self._path(storage_key)
        try:
            return path.open("rb")
        except FileNotFoundError as error:
            raise ArtifactStorageError("Artifact content is missing") from error

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)

    def exists(self, storage_key: str) -> bool:
        return self._path(storage_key).is_file()

    def get_metadata(self, storage_key: str) -> dict:
        path = self._path(storage_key)
        if not path.is_file():
            raise ArtifactStorageError("Artifact content is missing")
        stat = path.stat()
        return {"size": stat.st_size, "modified_at": stat.st_mtime}

    def verify(self, storage_key: str, expected_checksum: str) -> None:
        with self.read(storage_key) as source:
            digest = hashlib.sha256()
            while chunk := source.read(self.chunk_size):
                digest.update(chunk)
        if digest.hexdigest() != expected_checksum:
            raise ArtifactIntegrityError("Artifact checksum mismatch")
