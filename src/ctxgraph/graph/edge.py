"""Edge representation for relationships between code entities.

Edges are immutable, hashable objects representing directed relationships
between nodes in the code graph. Edges reference nodes by ID rather than
by object reference to simplify serialization.
"""

from dataclasses import dataclass, field
from typing import Any

from .types import EdgeType


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed edge in the code graph representing a relationship.

    Edges connect two nodes (source -> target) with a semantic relationship type.
    They are immutable and reference nodes by ID rather than object reference.

    Attributes:
        source_id: ID of the source node.
        target_id: ID of the target node.
        type: The semantic type of this relationship.
        metadata: Arbitrary additional information about the relationship.

    Examples:
        >>> edge = Edge(
        ...     source_id="myapp.module_a",
        ...     target_id="myapp.module_b",
        ...     type=EdgeType.IMPORTS,
        ...     metadata={"imported_names": ["foo", "bar"]},
        ... )
        >>> edge.source_id
        'myapp.module_a'
        >>> edge.type
        <EdgeType.IMPORTS: 1>
    """

    source_id: str
    target_id: str
    type: EdgeType
    metadata: dict[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        """Validate edge invariants."""
        if not self.source_id:
            raise ValueError("Edge source_id cannot be empty")
        if not self.target_id:
            raise ValueError("Edge target_id cannot be empty")

    def reversed(self) -> "Edge":
        """Return a new edge with source and target swapped.

        Returns:
            A new Edge with reversed direction and same type/metadata.

        Examples:
            >>> edge = Edge("a", "b", EdgeType.CALLS)
            >>> rev = edge.reversed()
            >>> rev.source_id
            'b'
            >>> rev.target_id
            'a'
        """
        from dataclasses import replace

        return replace(self, source_id=self.target_id, target_id=self.source_id)

    def with_metadata(self, **kwargs: Any) -> "Edge":
        """Create a new edge with additional metadata.

        Args:
            **kwargs: Key-value pairs to add to metadata.

        Returns:
            A new Edge instance with merged metadata.

        Examples:
            >>> edge = Edge("a", "b", EdgeType.CALLS)
            >>> enriched = edge.with_metadata(call_count=5, async_call=True)
            >>> enriched.metadata["call_count"]
            5
        """
        from dataclasses import replace

        new_metadata = {**self.metadata, **kwargs}
        return replace(self, metadata=new_metadata)

    @property
    def is_self_loop(self) -> bool:
        """Check if this edge is a self-loop (source == target).

        Returns:
            True if source_id equals target_id.
        """
        return self.source_id == self.target_id
