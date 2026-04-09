"""Graph-aware context retrieval engine.

This module provides intelligent context retrieval for LLMs and developers
using graph structure and hybrid text matching (no embeddings/vector DB).
"""

from dataclasses import dataclass, field

from ..graph import CodeGraph, Node, NodeType
from ..query import QueryEngine
from .scoring import CentralityScorer, ScoringWeights, TextMatcher


@dataclass
class ScoredNode:
    """A node with relevance score.

    Attributes:
        node: The graph node.
        score: Relevance score.
        score_breakdown: Breakdown of score components for debugging.
    """

    node: Node
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def __lt__(self, other: "ScoredNode") -> bool:
        """Compare by score for sorting."""
        return self.score < other.score


@dataclass
class RetrievalResult:
    """Result of context retrieval.

    Attributes:
        ranked_nodes: Nodes ranked by relevance.
        total_scored: Total number of nodes scored.
        query: Original query.
    """

    ranked_nodes: list[ScoredNode]
    total_scored: int
    query: str

    @property
    def top_node(self) -> ScoredNode | None:
        """Return the highest-scoring node."""
        return self.ranked_nodes[0] if self.ranked_nodes else None


@dataclass
class PackedContext:
    """Context packed within a token budget.

    Attributes:
        nodes: Nodes included in context.
        estimated_tokens: Estimated token count.
        token_budget: Original token budget.
        query: Original query.
    """

    nodes: list[Node]
    estimated_tokens: int
    token_budget: int
    query: str

    @property
    def utilization(self) -> float:
        """Return budget utilization percentage."""
        return (self.estimated_tokens / self.token_budget) * 100 if self.token_budget > 0 else 0


class RetrievalEngine:
    """Graph-aware context retrieval using hybrid scoring.

    This engine ranks code entities by relevance to a query using:
    - Symbol name matching
    - File path matching
    - Docstring/comment matching
    - Graph centrality (degree-based importance)
    - Node type preferences
    - Entrypoint proximity
    """

    def __init__(
        self,
        graph: CodeGraph,
        weights: ScoringWeights | None = None,
    ) -> None:
        """Initialize retrieval engine.

        Args:
            graph: Code graph to search.
            weights: Scoring weights (uses defaults if not provided).
        """
        self.graph = graph
        self.weights = weights or ScoringWeights()
        self.query_engine = QueryEngine(graph)
        self.text_matcher = TextMatcher()
        self.centrality_scorer = CentralityScorer()

    def rank_context_for_query(
        self,
        query: str,
        entrypoints: list[str] | None = None,
        max_results: int = 50,
    ) -> RetrievalResult:
        """Rank all nodes by relevance to query.

        Args:
            query: Search query (e.g., "user authentication", "database models").
            entrypoints: Optional list of entrypoint node IDs to bias towards.
            max_results: Maximum number of results to return.

        Returns:
            RetrievalResult with ranked nodes.

        Examples:
            >>> engine = RetrievalEngine(graph)
            >>> result = engine.rank_context_for_query("database models")
            >>> for scored in result.ranked_nodes[:5]:
            ...     print(f"{scored.node.id}: {scored.score:.2f}")
        """
        scored_nodes = []

        # Build entrypoint set for fast lookup
        entrypoint_set = set(entrypoints) if entrypoints else set()

        # Score each node
        for node in self.graph.nodes():
            score = self._score_node(node, query, entrypoint_set)
            if score.score > 0:  # Only include nodes with some relevance
                scored_nodes.append(score)

        # Sort by score (descending)
        scored_nodes.sort(reverse=True)

        # Limit results
        ranked = scored_nodes[:max_results]

        return RetrievalResult(
            ranked_nodes=ranked,
            total_scored=len(scored_nodes),
            query=query,
        )

    def pack_minimal_context(
        self,
        query: str,
        token_budget: int = 3000,
        entrypoints: list[str] | None = None,
        include_neighbors: bool = True,
    ) -> PackedContext:
        """Pack relevant context within a token budget.

        This method:
        1. Ranks nodes by relevance
        2. Greedily packs nodes in order of score
        3. Optionally includes immediate neighbors for completeness
        4. Stops when token budget is reached

        Args:
            query: Search query.
            token_budget: Maximum tokens to use (default: 3000).
            entrypoints: Optional entrypoint node IDs.
            include_neighbors: Whether to include immediate neighbors of top nodes.

        Returns:
            PackedContext with selected nodes and token estimate.

        Examples:
            >>> engine = RetrievalEngine(graph)
            >>> context = engine.pack_minimal_context(
            ...     "user authentication",
            ...     token_budget=2000
            ... )
            >>> print(f"Packed {len(context.nodes)} nodes")
            >>> print(f"Estimated tokens: {context.estimated_tokens}")
        """
        # Rank nodes
        ranked = self.rank_context_for_query(query, entrypoints)

        # Greedily pack nodes
        packed_nodes = []
        packed_ids = set()
        estimated_tokens = 0

        for scored in ranked.ranked_nodes:
            node = scored.node

            # Estimate tokens for this node
            node_tokens = self._estimate_node_tokens(node)

            # Always include at least the top node even if it exceeds the budget
            # on its own; otherwise skip nodes that don't fit and keep trying
            # smaller ones (budget is scored-order, not size-order).
            if estimated_tokens + node_tokens > token_budget:
                if not packed_nodes:
                    # Force-include the top result so the caller always gets something
                    packed_nodes.append(node)
                    packed_ids.add(node.id)
                    estimated_tokens += node_tokens
                continue

            # Add node
            packed_nodes.append(node)
            packed_ids.add(node.id)
            estimated_tokens += node_tokens

        # Optionally include neighbors for context completeness
        if include_neighbors:
            neighbor_nodes = []
            for node in packed_nodes[:]:  # Iterate over original list
                neighbors = self.query_engine.get_related_context(node.id, radius=1)

                for neighbor in neighbors.context_nodes:
                    if neighbor.id not in packed_ids:
                        neighbor_tokens = self._estimate_node_tokens(neighbor)

                        # Only add if budget allows
                        if estimated_tokens + neighbor_tokens <= token_budget:
                            neighbor_nodes.append(neighbor)
                            packed_ids.add(neighbor.id)
                            estimated_tokens += neighbor_tokens

            # Add neighbors to packed nodes
            packed_nodes.extend(neighbor_nodes)

        return PackedContext(
            nodes=packed_nodes,
            estimated_tokens=estimated_tokens,
            token_budget=token_budget,
            query=query,
        )

    def _score_node(
        self,
        node: Node,
        query: str,
        entrypoint_set: set[str],
    ) -> ScoredNode:
        """Score a single node for relevance to query.

        Args:
            node: Node to score.
            query: Search query.
            entrypoint_set: Set of entrypoint node IDs.

        Returns:
            ScoredNode with total score and breakdown.
        """
        breakdown: dict[str, float] = {}
        total_score = 0.0

        # 1. Name matching (most important)
        name_score = self.text_matcher.score_name_match(node.name, query)
        if name_score > 0:
            breakdown["name_match"] = name_score
            total_score += name_score

        # 2. Path matching
        if node.file_path:
            path_score = self.text_matcher.score_path_match(node.file_path, query)
            if path_score > 0:
                weighted = path_score * (self.weights.path_match / 3.0)
                breakdown["path_match"] = weighted
                total_score += weighted

        # 3. Docstring matching
        docstring = node.metadata.get("docstring")
        if docstring:
            doc_score = self.text_matcher.score_text_match(docstring, query)
            if doc_score > 0:
                weighted = doc_score * (self.weights.docstring_match / 5.0)
                breakdown["docstring_match"] = weighted
                total_score += weighted

        # 4. Graph centrality
        in_degree = len(self.graph.get_incoming_edges(node.id))
        out_degree = len(self.graph.get_outgoing_edges(node.id))

        centrality = self.centrality_scorer.score_degree_centrality(in_degree, out_degree)
        if centrality > 0:
            weighted = centrality * (self.weights.centrality / 3.0)
            breakdown["centrality"] = weighted
            total_score += weighted

        # 5. Type bonus (prefer functions and classes over modules)
        if node.type in (NodeType.FUNCTION, NodeType.CLASS):
            breakdown["type_bonus"] = self.weights.type_bonus
            total_score += self.weights.type_bonus

        # 6. Entrypoint proximity bonus
        if node.id in entrypoint_set:
            # Direct entrypoint
            breakdown["entrypoint_bonus"] = self.weights.entrypoint_bonus
            total_score += self.weights.entrypoint_bonus
        elif entrypoint_set:
            # Check if node is near an entrypoint (1 hop)
            for entrypoint_id in entrypoint_set:
                if self.graph.has_node(entrypoint_id):
                    neighbors = self.query_engine.get_related_context(entrypoint_id, radius=1)
                    if any(n.id == node.id for n in neighbors.context_nodes):
                        weighted = self.weights.entrypoint_bonus * 0.5
                        breakdown["entrypoint_proximity"] = weighted
                        total_score += weighted
                        break  # Only count once

        return ScoredNode(
            node=node,
            score=total_score,
            score_breakdown=breakdown,
        )

    def _estimate_node_tokens(self, node: Node) -> int:
        """Estimate token count for a node.

        This is a rough heuristic:
        - Count lines of code
        - Assume ~4 tokens per line (average for code)
        - Add tokens for docstring/metadata

        Args:
            node: Node to estimate.

        Returns:
            Estimated token count.
        """
        tokens = 0

        # Estimate based on source location
        if node.location:
            lines = node.location.line_end - node.location.line_start + 1
            tokens += lines * 4  # ~4 tokens per line of code

        # Add tokens for docstring
        docstring = node.metadata.get("docstring")
        if docstring:
            # Rough estimate: 1 token per 4 characters
            tokens += len(docstring) // 4

        # Minimum token count
        tokens = max(tokens, 10)  # At least 10 tokens per node

        return tokens


def rank_context_for_query(
    graph: CodeGraph,
    query: str,
    entrypoints: list[str] | None = None,
    weights: ScoringWeights | None = None,
) -> RetrievalResult:
    """Convenience function to rank context for a query.

    Args:
        graph: Code graph to search.
        query: Search query.
        entrypoints: Optional entrypoint node IDs.
        weights: Optional custom scoring weights.

    Returns:
        RetrievalResult with ranked nodes.

    Examples:
        >>> result = rank_context_for_query(graph, "user models")
        >>> print(f"Found {len(result.ranked_nodes)} relevant nodes")
    """
    engine = RetrievalEngine(graph, weights)
    return engine.rank_context_for_query(query, entrypoints)


def pack_minimal_context(
    graph: CodeGraph,
    query: str,
    token_budget: int = 3000,
    entrypoints: list[str] | None = None,
    weights: ScoringWeights | None = None,
) -> PackedContext:
    """Convenience function to pack context within a token budget.

    Args:
        graph: Code graph to search.
        query: Search query.
        token_budget: Maximum tokens to use.
        entrypoints: Optional entrypoint node IDs.
        weights: Optional custom scoring weights.

    Returns:
        PackedContext with selected nodes.

    Examples:
        >>> context = pack_minimal_context(graph, "authentication", token_budget=2000)
        >>> print(f"Utilization: {context.utilization:.1f}%")
    """
    engine = RetrievalEngine(graph, weights)
    return engine.pack_minimal_context(query, token_budget, entrypoints)
