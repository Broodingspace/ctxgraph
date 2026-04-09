"""Core graph data structures for ctxgraph.

This module provides the fundamental building blocks for representing code
as a queryable graph: nodes, edges, and the graph container.
"""

from .edge import Edge
from .graph import CodeGraph
from .node import Node, SourceLocation
from .types import EdgeType, NodeType

__all__ = [
    "CodeGraph",
    "Node",
    "Edge",
    "SourceLocation",
    "NodeType",
    "EdgeType",
]
