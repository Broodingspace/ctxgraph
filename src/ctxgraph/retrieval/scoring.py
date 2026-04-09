"""Scoring utilities for context retrieval.

This module provides scoring functions for ranking code entities based on
relevance to a query without using embeddings or vector databases.
"""

import re
from dataclasses import dataclass


@dataclass
class ScoringWeights:
    """Configurable weights for different scoring components.

    Attributes:
        name_exact_match: Weight for exact name match.
        name_starts_with: Weight for name starting with query.
        name_contains: Weight for name containing query.
        name_fuzzy: Weight for fuzzy name match.
        path_match: Weight for path containing query.
        docstring_match: Weight for docstring containing query.
        centrality: Weight for graph centrality score.
        type_bonus: Weight for specific node types.
        entrypoint_bonus: Weight for being near entrypoints.
    """

    name_exact_match: float = 10.0
    name_starts_with: float = 7.0
    name_contains: float = 5.0
    name_fuzzy: float = 2.0
    path_match: float = 3.0
    docstring_match: float = 4.0
    centrality: float = 2.0
    type_bonus: float = 1.5
    entrypoint_bonus: float = 5.0


class TextMatcher:
    """Text matching utilities for scoring."""

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for matching.

        Args:
            text: Text to normalize.

        Returns:
            Normalized text (lowercase, no underscores).
        """
        return text.lower().replace("_", "").replace("-", "")

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text into searchable terms.

        Args:
            text: Text to tokenize.

        Returns:
            List of tokens.
        """
        # Split on common delimiters
        tokens = re.split(r"[._\-\s/]+", text.lower())
        return [t for t in tokens if t]

    @staticmethod
    def score_name_match(name: str, query: str) -> float:
        """Score how well a name matches a query.

        Args:
            name: Node name to score.
            query: Query string.

        Returns:
            Match score (0-10).
        """
        name_norm = TextMatcher.normalize(name)
        query_norm = TextMatcher.normalize(query)

        # Exact match
        if name_norm == query_norm:
            return 10.0

        # Starts with
        if name_norm.startswith(query_norm):
            return 7.0

        # Contains
        if query_norm in name_norm:
            return 5.0

        # Token overlap (fuzzy)
        name_tokens = set(TextMatcher.tokenize(name))
        query_tokens = set(TextMatcher.tokenize(query))

        if name_tokens & query_tokens:
            overlap = len(name_tokens & query_tokens)
            total = len(query_tokens)
            return 2.0 * (overlap / total) if total > 0 else 0.0

        return 0.0

    @staticmethod
    def score_text_match(text: str | None, query: str) -> float:
        """Score how well text contains query terms.

        Args:
            text: Text to search (e.g., docstring).
            query: Query string.

        Returns:
            Match score (0-5).
        """
        if not text:
            return 0.0

        text_norm = TextMatcher.normalize(text)
        query_norm = TextMatcher.normalize(query)

        # Full query match
        if query_norm in text_norm:
            return 5.0

        # Token overlap
        text_tokens = set(TextMatcher.tokenize(text))
        query_tokens = set(TextMatcher.tokenize(query))

        overlap = len(text_tokens & query_tokens)
        total = len(query_tokens)

        if overlap > 0 and total > 0:
            return 4.0 * (overlap / total)

        return 0.0

    @staticmethod
    def score_path_match(path: str | None, query: str) -> float:
        """Score how well a file path matches query.

        Args:
            path: File path.
            query: Query string.

        Returns:
            Match score (0-3).
        """
        if not path:
            return 0.0

        path_norm = TextMatcher.normalize(path)
        query_norm = TextMatcher.normalize(query)

        # Path contains query
        if query_norm in path_norm:
            return 3.0

        # Token overlap
        path_tokens = set(TextMatcher.tokenize(path))
        query_tokens = set(TextMatcher.tokenize(query))

        overlap = len(path_tokens & query_tokens)
        total = len(query_tokens)

        if overlap > 0 and total > 0:
            return 2.0 * (overlap / total)

        return 0.0


class CentralityScorer:
    """Graph centrality scoring for node importance."""

    @staticmethod
    def score_degree_centrality(in_degree: int, out_degree: int, max_degree: int = 50) -> float:
        """Score node importance based on degree centrality.

        Args:
            in_degree: Number of incoming edges.
            out_degree: Number of outgoing edges.
            max_degree: Maximum degree for normalization.

        Returns:
            Centrality score (0-3).
        """
        # Nodes with more connections are more "central"
        total_degree = in_degree + out_degree

        # Normalize to 0-3 range
        normalized = min(total_degree / max_degree, 1.0)
        return normalized * 3.0

    @staticmethod
    def score_hub_authority(in_degree: int, out_degree: int) -> tuple[float, float]:
        """Score node as hub (many outgoing) or authority (many incoming).

        Args:
            in_degree: Number of incoming edges.
            out_degree: Number of outgoing edges.

        Returns:
            Tuple of (hub_score, authority_score), each 0-2.
        """
        # Hubs have many outgoing edges (they point to others)
        hub_score = min(out_degree / 10.0, 1.0) * 2.0

        # Authorities have many incoming edges (others point to them)
        authority_score = min(in_degree / 10.0, 1.0) * 2.0

        return hub_score, authority_score
