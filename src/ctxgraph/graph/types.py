"""Type definitions for nodes and edges in the code graph.

This module defines the semantic types for graph entities, enabling
type-safe graph construction and querying.
"""

from enum import Enum, auto


class NodeType(Enum):
    """Types of nodes in the code graph.

    Each node type represents a distinct code entity that can be analyzed
    and connected to other entities via edges.
    """

    MODULE = auto()
    """A Python module (file or package)."""

    CLASS = auto()
    """A class definition."""

    FUNCTION = auto()
    """A function or method definition."""

    VARIABLE = auto()
    """A module-level or class-level variable."""

    CALL_SITE = auto()
    """A specific location where a function is called (for fine-grained analysis)."""


class EdgeType(Enum):
    """Types of edges in the code graph.

    Each edge type represents a semantic relationship between code entities,
    enabling traversal and queries about code structure.
    """

    IMPORTS = auto()
    """Module A imports Module B (or specific symbols from B)."""

    DEFINES = auto()
    """Container entity defines a nested entity (Module defines Class/Function)."""

    CONTAINS = auto()
    """Scoping relationship (Module contains Class, Class contains Method)."""

    CALLS = auto()
    """Function A calls Function B."""

    INHERITS = auto()
    """Class A inherits from Class B."""

    USES = auto()
    """Function/method uses a variable or attribute."""

    REFERENCES = auto()
    """General reference relationship (fallback for other relationships)."""
