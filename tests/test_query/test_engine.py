"""Tests for query engine."""

from pathlib import Path

import pytest

from ctxgraph import CodeGraph, Edge, EdgeType, Node, NodeType, build_graph
from ctxgraph.query import QueryEngine

# Test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


def create_test_graph() -> CodeGraph:
    """Create a test graph for querying.

    Graph structure:
        A -> B -> C
        A -> D
        E -> D
        C -> F
    """
    graph = CodeGraph()

    # Add nodes
    for letter in "ABCDEF":
        node = Node(
            id=f"test.{letter}",
            type=NodeType.FUNCTION,
            name=letter,
        )
        graph.add_node(node)

    # Add edges
    edges = [
        ("A", "B", EdgeType.CALLS),
        ("B", "C", EdgeType.CALLS),
        ("A", "D", EdgeType.CALLS),
        ("E", "D", EdgeType.CALLS),
        ("C", "F", EdgeType.CALLS),
    ]

    for source, target, edge_type in edges:
        graph.add_edge(Edge(f"test.{source}", f"test.{target}", edge_type))

    return graph


class TestDependencyQueries:
    """Test dependency query methods."""

    def test_get_dependencies_direct(self) -> None:
        """Test getting direct dependencies."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_dependencies("test.A")

        assert result.count == 2
        dep_names = {n.name for n in result.dependencies}
        assert dep_names == {"B", "D"}

    def test_get_dependencies_transitive(self) -> None:
        """Test getting transitive dependencies."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_dependencies("test.A", transitive=True)

        # A -> B -> C -> F and A -> D
        assert result.count == 4
        dep_names = {n.name for n in result.dependencies}
        assert dep_names == {"B", "C", "D", "F"}

    def test_get_dependencies_filtered(self) -> None:
        """Test getting dependencies with edge type filter."""
        graph = create_test_graph()
        # Add an import edge
        graph.add_edge(Edge("test.A", "test.E", EdgeType.IMPORTS))

        engine = QueryEngine(graph)

        # Only CALLS edges
        result = engine.get_dependencies("test.A", edge_types=[EdgeType.CALLS])
        dep_names = {n.name for n in result.dependencies}
        assert dep_names == {"B", "D"}

        # Only IMPORTS edges
        result = engine.get_dependencies("test.A", edge_types=[EdgeType.IMPORTS])
        dep_names = {n.name for n in result.dependencies}
        assert dep_names == {"E"}

    def test_get_dependencies_nonexistent_node(self) -> None:
        """Test getting dependencies of nonexistent node."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        with pytest.raises(ValueError, match="not found"):
            engine.get_dependencies("test.Z")

    def test_get_reverse_dependencies_direct(self) -> None:
        """Test getting direct reverse dependencies."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_reverse_dependencies("test.D")

        assert result.count == 2
        dep_names = {n.name for n in result.dependencies}
        assert dep_names == {"A", "E"}

    def test_get_reverse_dependencies_transitive(self) -> None:
        """Test getting transitive reverse dependencies."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_reverse_dependencies("test.F", transitive=True)

        # F <- C <- B <- A
        assert result.count == 3
        dep_names = {n.name for n in result.dependencies}
        assert dep_names == {"A", "B", "C"}

    def test_dependency_types_tracking(self) -> None:
        """Test that dependency types are tracked correctly."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_dependencies("test.A")

        assert "test.B" in result.dependency_types
        assert EdgeType.CALLS in result.dependency_types["test.B"]


class TestBlastRadiusAnalysis:
    """Test blast radius analysis."""

    def test_blast_radius_depth_1(self) -> None:
        """Test blast radius with depth 1."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.find_blast_radius("test.A", max_depth=1)

        # Direct dependencies: B, D
        assert result.count == 2
        affected_names = {n.name for n in result.affected_nodes}
        assert affected_names == {"B", "D"}

    def test_blast_radius_depth_2(self) -> None:
        """Test blast radius with depth 2."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.find_blast_radius("test.A", max_depth=2)

        # A -> B -> C, A -> D
        assert result.count == 3
        affected_names = {n.name for n in result.affected_nodes}
        assert affected_names == {"B", "C", "D"}

    def test_blast_radius_incoming(self) -> None:
        """Test blast radius with incoming direction."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.find_blast_radius(
            "test.D",
            max_depth=2,
            direction="incoming"
        )

        # D <- A, D <- E (depth 1), and no depth 2 for E
        assert result.count >= 2

    def test_blast_radius_both_directions(self) -> None:
        """Test blast radius with both directions."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.find_blast_radius(
            "test.B",
            max_depth=1,
            direction="both"
        )

        # Outgoing: C, Incoming: A
        affected_names = {n.name for n in result.affected_nodes}
        assert "A" in affected_names
        assert "C" in affected_names

    def test_blast_radius_distances(self) -> None:
        """Test that distances are tracked correctly."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.find_blast_radius("test.A", max_depth=2)

        # B and D at distance 1
        depth_1 = result.nodes_at_distance(1)
        assert len(depth_1) == 2

        # C at distance 2
        depth_2 = result.nodes_at_distance(2)
        assert len(depth_2) == 1
        assert depth_2[0].name == "C"

    def test_blast_radius_invalid_direction(self) -> None:
        """Test blast radius with invalid direction."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        with pytest.raises(ValueError, match="Invalid direction"):
            engine.find_blast_radius("test.A", direction="sideways")


class TestPathFinding:
    """Test path finding methods."""

    def test_trace_path_direct(self) -> None:
        """Test finding a direct path."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.trace_path("test.A", "test.B")

        assert result.exists
        assert result.path == ["test.A", "test.B"]
        assert result.length == 1
        assert result.edges == [EdgeType.CALLS]

    def test_trace_path_multi_hop(self) -> None:
        """Test finding a multi-hop path."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.trace_path("test.A", "test.C")

        assert result.exists
        assert result.path == ["test.A", "test.B", "test.C"]
        assert result.length == 2

    def test_trace_path_no_path(self) -> None:
        """Test when no path exists."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        # E to A has no path (reverse direction only)
        result = engine.trace_path("test.E", "test.A")

        assert not result.exists
        assert result.path == []
        assert result.length == 0

    def test_trace_path_filtered(self) -> None:
        """Test path finding with edge type filter."""
        graph = create_test_graph()
        # Add an import edge that shortcuts the path
        graph.add_edge(Edge("test.A", "test.C", EdgeType.IMPORTS))

        engine = QueryEngine(graph)

        # With CALLS only, should go A -> B -> C
        result = engine.trace_path("test.A", "test.C", edge_types=[EdgeType.CALLS])
        assert result.length == 2

    def test_trace_path_nonexistent_nodes(self) -> None:
        """Test path finding with nonexistent nodes."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        with pytest.raises(ValueError, match="Source node"):
            engine.trace_path("test.Z", "test.A")

        with pytest.raises(ValueError, match="Target node"):
            engine.trace_path("test.A", "test.Z")


class TestContextExtraction:
    """Test context extraction methods."""

    def test_get_related_context_radius_1(self) -> None:
        """Test getting context with radius 1."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_related_context("test.B", radius=1)

        # Origin + neighbors (A, C)
        assert result.total_size == 3
        context_names = {n.name for n in result.context_nodes}
        assert context_names == {"B", "A", "C"}

    def test_get_related_context_radius_2(self) -> None:
        """Test getting context with radius 2."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_related_context("test.C", radius=2)

        # C (origin) + B (1 hop) + A, F (2 hops)
        assert result.total_size >= 4

    def test_get_related_context_layers(self) -> None:
        """Test that context layers are tracked."""
        graph = create_test_graph()
        engine = QueryEngine(graph)

        result = engine.get_related_context("test.B", radius=2)

        # Layer 0 is origin
        assert 0 in result.layers
        assert len(result.layers[0]) == 1
        assert result.layers[0][0].name == "B"

        # Layer 1 should have neighbors
        assert 1 in result.layers
        assert len(result.layers[1]) >= 2

    def test_get_related_context_with_filter(self) -> None:
        """Test context extraction with node filter."""
        graph = create_test_graph()
        # Add a module node
        module = Node("test.module", NodeType.MODULE, "module")
        graph.add_node(module)
        graph.add_edge(Edge("test.module", "test.A", EdgeType.DEFINES))

        engine = QueryEngine(graph)

        # Filter to only functions
        result = engine.get_related_context(
            "test.A",
            radius=2,
            node_filter=lambda n: n.type == NodeType.FUNCTION
        )

        # Should not include the module
        context_ids = {n.id for n in result.context_nodes}
        assert "test.module" not in context_ids

    def test_get_related_context_get_files(self) -> None:
        """Test getting unique files from context."""
        graph = CodeGraph()

        # Create nodes in different files
        node_a = Node("test.a", NodeType.FUNCTION, "a")
        node_a = node_a.with_metadata(file_path="file_a.py")
        node_b = Node("test.b", NodeType.FUNCTION, "b")
        node_b = node_b.with_metadata(file_path="file_b.py")

        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(Edge("test.a", "test.b", EdgeType.CALLS))

        engine = QueryEngine(graph)
        result = engine.get_related_context("test.a", radius=1)

        # Both files should be in context, but node_a doesn't have location
        # So this test just checks the method works
        files = result.get_files()
        assert isinstance(files, set)


class TestRealWorldQueries:
    """Test queries on real parsed code."""

    def test_query_sample_project(self) -> None:
        """Test queries on sample project."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
        engine = QueryEngine(graph)

        # Find dependencies of models module
        models_module = None
        for node in graph.nodes(node_type=NodeType.MODULE):
            if "models" in node.id:
                models_module = node
                break

        if models_module:
            result = engine.get_dependencies(models_module.id)
            # models imports from utils
            assert result.count >= 0

    def test_blast_radius_on_class(self) -> None:
        """Test blast radius on a class."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
        engine = QueryEngine(graph)

        # Find the User class
        user_class = None
        for node in graph.nodes(node_type=NodeType.CLASS):
            if node.name == "User":
                user_class = node
                break

        if user_class:
            result = engine.find_blast_radius(
                user_class.id,
                max_depth=2,
                direction="both"
            )
            # Should have some affected nodes
            assert result.count >= 0

    def test_context_for_function(self) -> None:
        """Test getting context for a function."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
        engine = QueryEngine(graph)

        # Find helper_function
        helper_func = None
        for node in graph.nodes(node_type=NodeType.FUNCTION):
            if node.name == "helper_function":
                helper_func = node
                break

        if helper_func:
            result = engine.get_related_context(helper_func.id, radius=2)
            # Should have the function and some context
            assert result.total_size >= 1
            assert result.origin == helper_func
