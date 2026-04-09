"""Query engine for ctxgraph.

This module provides high-level APIs for querying code graphs to extract
insights about dependencies, impact, paths, and context.
"""

from .engine import (
    BlastRadiusResult,
    ContextResult,
    DependencyResult,
    PathResult,
    QueryEngine,
)

__all__ = [
    "QueryEngine",
    "DependencyResult",
    "BlastRadiusResult",
    "PathResult",
    "ContextResult",
]
