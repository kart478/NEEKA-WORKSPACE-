import sqlite3
from pathlib import Path


def backup_database(source: str | Path, destination: str | Path) -> Path:
    """Create a consistent SQLite backup using SQLite's backup API."""
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_path) as source_connection, sqlite3.connect(destination_path) as destination_connection:
        source_connection.backup(destination_connection)
    return destination_path