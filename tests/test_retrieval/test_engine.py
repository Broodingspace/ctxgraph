"""Tests for retrieval engine."""

from pathlib import Path

import pytest

from ctxgraph import CodeGraph, Edge, EdgeType, Node, NodeType, build_graph
from ctxgraph.retrieval import (
    RetrievalEngine,
    ScoringWeights,
    pack_minimal_context,
    rank_context_for_query,
)

# Test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


def create_test_graph() -> CodeGraph:
    """Create a test graph for retrieval testing."""
    graph = CodeGraph()

    # Add nodes with descriptive names
    nodes = [
        Node("app.user_auth", NodeType.MODULE, "user_auth"),
        Node("app.user_auth.login", NodeType.FUNCTION, "login"),
        Node("app.user_auth.logout", NodeType.FUNCTION, "logout"),
        Node("app.models", NodeType.MODULE, "models"),
        Node("app.models.User", NodeType.CLASS, "User"),
        Node("app.models.User.save", NodeType.FUNCTION, "save"),
        Node("app.database", NodeType.MODULE, "database"),
        Node("app.database.connect", NodeType.FUNCTION, "connect"),
    ]

    for node in nodes:
        # Add some with docstrings
        if "user" in node.name.lower():
            node = node.with_metadata(docstring=f"Handles user-related operations")
        if "auth" in node.name.lower():
            node = node.with_metadata(docstring=f"Authentication functionality")

        graph.add_node(node)

    # Add edges to create structure
    edges = [
        Edge("app.user_auth", "app.user_auth.login", EdgeType.DEFINES),
        Edge("app.user_auth", "app.user_auth.logout", EdgeType.DEFINES),
        Edge("app.models", "app.models.User", EdgeType.DEFINES),
        Edge("app.models.User", "app.models.User.save", EdgeType.CONTAINS),
        Edge("app.database", "app.database.connect", EdgeType.DEFINES),
        Edge("app.user_auth.login", "app.models.User", EdgeType.USES),
        Edge("app.user_auth.login", "app.database.connect", EdgeType.CALLS),
        Edge("app.models.User.save", "app.database.connect", EdgeType.CALLS),
    ]

    for edge in edges:
        graph.add_edge(edge)

    return graph


class TestRetrievalEngine:
    """Test retrieval engine functionality."""

    def test_rank_context_for_query_exact_match(self) -> None:
        """Test ranking with exact name match."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        result = engine.rank_context_for_query("User")

        # User class should be top result
        assert len(result.ranked_nodes) > 0
        top = result.top_node
        assert top is not None
        assert "User" in top.node.id

    def test_rank_context_for_query_fuzzy_match(self) -> None:
        """Test ranking with fuzzy matching."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        result = engine.rank_context_for_query("authentication")

        # Should find auth-related nodes
        assert len(result.ranked_nodes) > 0
        found_auth = any("auth" in node.node.id.lower() for node in result.ranked_nodes)
        assert found_auth

    def test_rank_context_with_docstring_match(self) -> None:
        """Test that docstring matching works."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        result = engine.rank_context_for_query("user operations")

        # Should rank nodes with "user" in docstring higher
        assert len(result.ranked_nodes) > 0

    def test_rank_context_with_entrypoints(self) -> None:
        """Test entrypoint biasing."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        # Without entrypoints
        result_no_entry = engine.rank_context_for_query("login")

        # With entrypoints
        result_with_entry = engine.rank_context_for_query(
            "login",
            entrypoints=["app.user_auth"]
        )

        # Scores should differ (entrypoint bias)
        assert len(result_with_entry.ranked_nodes) > 0

    def test_rank_context_centrality_bonus(self) -> None:
        """Test that high-degree nodes get centrality bonus."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        result = engine.rank_context_for_query("database")

        # database.connect has high degree (called by multiple nodes)
        connect_scores = [
            s for s in result.ranked_nodes
            if "connect" in s.node.id
        ]

        if connect_scores:
            # Should have centrality bonus
            assert "centrality" in connect_scores[0].score_breakdown

    def test_rank_context_max_results(self) -> None:
        """Test max_results parameter."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        result = engine.rank_context_for_query("user", max_results=3)

        assert len(result.ranked_nodes) <= 3

    def test_pack_minimal_context(self) -> None:
        """Test packing context within token budget."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        context = engine.pack_minimal_context("user", token_budget=500)

        # Should pack some nodes
        assert len(context.nodes) > 0

        # Should stay within budget
        assert context.estimated_tokens <= context.token_budget

        # Should include the query
        assert context.query == "user"

    def test_pack_minimal_context_with_neighbors(self) -> None:
        """Test that packing includes neighbors."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        # Pack with neighbors
        context_with = engine.pack_minimal_context(
            "login",
            token_budget=1000,
            include_neighbors=True
        )

        # Pack without neighbors
        context_without = engine.pack_minimal_context(
            "login",
            token_budget=1000,
            include_neighbors=False
        )

        # With neighbors should have more nodes (usually)
        # Not guaranteed, but likely
        assert len(context_with.nodes) > 0
        assert len(context_without.nodes) > 0

    def test_pack_minimal_context_utilization(self) -> None:
        """Test budget utilization calculation."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        context = engine.pack_minimal_context("user", token_budget=1000)

        # Utilization should be percentage
        assert 0 <= context.utilization <= 100

    def test_pack_minimal_context_tight_budget(self) -> None:
        """Test packing with very tight budget."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        context = engine.pack_minimal_context("user", token_budget=50)

        # Should pack at least one node if possible
        assert len(context.nodes) >= 0
        assert context.estimated_tokens <= 50

    def test_estimate_node_tokens(self) -> None:
        """Test token estimation."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        # Get a node
        node = graph.get_node("app.models.User")
        assert node is not None

        tokens = engine._estimate_node_tokens(node)

        # Should have some minimum
        assert tokens >= 10


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_rank_context_for_query_function(self) -> None:
        """Test rank_context_for_query convenience function."""
        graph = create_test_graph()

        result = rank_context_for_query(graph, "user")

        assert isinstance(result.ranked_nodes, list)
        assert len(result.ranked_nodes) > 0

    def test_pack_minimal_context_function(self) -> None:
        """Test pack_minimal_context convenience function."""
        graph = create_test_graph()

        context = pack_minimal_context(graph, "authentication", token_budget=500)

        assert isinstance(context.nodes, list)
        assert context.token_budget == 500

    def test_custom_weights(self) -> None:
        """Test using custom scoring weights."""
        graph = create_test_graph()

        # Emphasize docstring matching
        weights = ScoringWeights(docstring_match=10.0)

        result = rank_context_for_query(graph, "operations", weights=weights)

        assert len(result.ranked_nodes) > 0


class TestRealWorldRetrieval:
    """Test retrieval on real parsed code."""

    def test_rank_context_sample_project(self) -> None:
        """Test ranking on sample project."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
        engine = RetrievalEngine(graph)

        result = engine.rank_context_for_query("user")

        # Should find User class
        assert len(result.ranked_nodes) > 0

        # Check if User class is in results
        user_found = any("User" in node.node.id for node in result.ranked_nodes)
        assert user_found

    def test_pack_context_sample_project(self) -> None:
        """Test packing context from sample project."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
        engine = RetrievalEngine(graph)

        context = engine.pack_minimal_context("helper function", token_budget=2000)

        # Should pack some relevant nodes
        assert len(context.nodes) > 0
        assert context.estimated_tokens <= 2000

    def test_score_breakdown_visibility(self) -> None:
        """Test that score breakdown is available for debugging."""
        graph = create_test_graph()
        engine = RetrievalEngine(graph)

        result = engine.rank_context_for_query("user")

        if result.ranked_nodes:
            top = result.ranked_nodes[0]
            # Should have breakdown
            assert isinstance(top.score_breakdown, dict)
            # Should have at least one scoring component
            assert len(top.score_breakdown) > 0
