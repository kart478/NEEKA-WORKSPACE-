from pathlib import PurePath


def build_metadata(name: str, mime_type: str, size: int, checksum: str, custom: dict | None = None) -> dict:
    suffix = PurePath(name).suffix.lower()
    return {
        "filename": name,
        "mime_type": mime_type,
        "size": size,
        "checksum": checksum,
        "extension": suffix[1:] if suffix else "",
        **(custom or {}),
    }
