"""Database abstraction layer for the sample project."""

from pathlib import Path


class DatabaseError(Exception):
    """Raised when a database operation fails."""


class Connection:
    """Represents a database connection."""

    def __init__(self, url: str) -> None:
        """Initialize connection.

        Args:
            url: Database connection URL.
        """
        self.url = url
        self._open = False

    def open(self) -> None:
        """Open the database connection."""
        self._open = True

    def close(self) -> None:
        """Close the database connection."""
        self._open = False

    @property
    def is_open(self) -> bool:
        """Return True if connection is open."""
        return self._open


class Repository:
    """Generic data repository backed by a connection."""

    def __init__(self, connection: Connection) -> None:
        """Initialize repository.

        Args:
            connection: Active database connection.
        """
        self.connection = connection

    def find_by_id(self, entity_id: int) -> dict | None:
        """Find a record by primary key.

        Args:
            entity_id: Primary key to look up.

        Returns:
            Record dict or None if not found.
        """
        if not self.connection.is_open:
            raise DatabaseError("Connection is not open")
        return None  # Stub

    def save(self, record: dict) -> dict:
        """Persist a record.

        Args:
            record: Record to persist.

        Returns:
            Persisted record with any generated fields.
        """
        if not self.connection.is_open:
            raise DatabaseError("Connection is not open")
        return record


def get_default_connection() -> Connection:
    """Return the default database connection for this environment.

    Returns:
        A Connection pointed at the default database URL.
    """
    url = "sqlite:///sample.db"
    conn = Connection(url)
    conn.open()
    return conn
