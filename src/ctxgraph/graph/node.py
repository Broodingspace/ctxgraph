"""Node representation for code graph entities.

Nodes are immutable, hashable objects representing code entities like modules,
classes, and functions. Each node carries metadata about its source location
and properties.
"""

from dataclasses import dataclass, field
from typing import Any

from .types import NodeType


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Precise location of a code entity in source files.

    Attributes:
        file_path: Absolute or relative path to the source file.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed, inclusive).
        column_start: Starting column (0-indexed), optional.
        column_end: Ending column (0-indexed, inclusive), optional.
    """

    file_path: str
    line_start: int
    line_end: int
    column_start: int | None = None
    column_end: int | None = None

    def __post_init__(self) -> None:
        """Validate source location invariants."""
        if self.line_start < 1 or self.line_end < 1:
            raise ValueError("Line numbers must be >= 1")
        if self.line_end < self.line_start:
            raise ValueError("line_end must be >= line_start")
        if self.column_start is not None and self.column_start < 0:
            raise ValueError("column_start must be >= 0")
        if self.column_end is not None and self.column_end < 0:
            raise ValueError("column_end must be >= 0")


@dataclass(frozen=True, slots=True)
class Node:
    """A node in the code graph representing a code entity.

    Nodes are immutable and uniquely identified by their ID. The ID should be
    constructed to be globally unique within a codebase (e.g., fully qualified name).

    Attributes:
        id: Unique identifier (e.g., "mypackage.module.ClassName.method_name").
        type: The semantic type of this node (module, class, function, etc.).
        name: Human-readable name of the entity (e.g., "method_name").
        location: Source location of this entity, if available.
        metadata: Arbitrary additional information (docstrings, type hints, etc.).

    Examples:
        >>> node = Node(
        ...     id="myapp.utils.helper_function",
        ...     type=NodeType.FUNCTION,
        ...     name="helper_function",
        ...     location=SourceLocation("myapp/utils.py", 10, 15),
        ... )
        >>> node.id
        'myapp.utils.helper_function'
        >>> node.type
        <NodeType.FUNCTION: 3>
    """

    id: str
    type: NodeType
    name: str
    location: SourceLocation | None = None
    metadata: dict[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        """Validate node invariants."""
        if not self.id:
            raise ValueError("Node ID cannot be empty")
        if not self.name:
            raise ValueError("Node name cannot be empty")

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified name (same as ID by convention)."""
        return self.id

    @property
    def file_path(self) -> str | None:
        """Return the file path if location is available."""
        return self.location.file_path if self.location else None

    def with_metadata(self, **kwargs: Any) -> "Node":
        """Create a new node with additional metadata.

        Args:
            **kwargs: Key-value pairs to add to metadata.

        Returns:
            A new Node instance with merged metadata.

        Examples:
            >>> original = Node(id="foo", type=NodeType.FUNCTION, name="foo")
            >>> enriched = original.with_metadata(docstring="Does foo things", async_=True)
            >>> enriched.metadata["docstring"]
            'Does foo things'
        """
        # Since we're frozen, we need to use object.__setattr__ workaround
        # or use dataclasses.replace
        from dataclasses import replace

        new_metadata = {**self.metadata, **kwargs}
        return replace(self, metadata=new_metadata)
