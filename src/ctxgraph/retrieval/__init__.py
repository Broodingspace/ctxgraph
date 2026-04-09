"""Graph-aware context retrieval for ctxgraph.

This module provides intelligent context retrieval using graph structure
and hybrid text matching (no embeddings or vector databases required).
"""

from .engine import (
    PackedContext,
    RetrievalEngine,
    RetrievalResult,
    ScoredNode,
    pack_minimal_context,
    rank_context_for_query,
)
from .scoring import CentralityScorer, ScoringWeights, TextMatcher

__all__ = [
    # Main API
    "RetrievalEngine",
    "rank_context_for_query",
    "pack_minimal_context",
    # Result types
    "RetrievalResult",
    "PackedContext",
    "ScoredNode",
    # Scoring utilities
    "ScoringWeights",
    "TextMatcher",
    "CentralityScorer",
]
