"""Tests for the core CodeGraph functionality."""

import pytest

from ctxgraph import CodeGraph, Edge, EdgeType, Node, NodeType, SourceLocation


class TestNode:
    """Test Node dataclass."""

    def test_create_node(self) -> None:
        """Test creating a basic node."""
        node = Node(id="test.foo", type=NodeType.FUNCTION, name="foo")
        assert node.id == "test.foo"
        assert node.type == NodeType.FUNCTION
        assert node.name == "foo"
        assert node.location is None
        assert node.metadata == {}

    def test_node_with_location(self) -> None:
        """Test creating a node with source location."""
        loc = SourceLocation("test.py", 10, 20)
        node = Node(id="test.foo", type=NodeType.FUNCTION, name="foo", location=loc)
        assert node.location == loc
        assert node.file_path == "test.py"

    def test_node_with_metadata(self) -> None:
        """Test adding metadata to a node."""
        node = Node(
            id="test.foo",
            type=NodeType.FUNCTION,
            name="foo",
            metadata={"docstring": "test", "async": True},
        )
        assert node.metadata["docstring"] == "test"
        assert node.metadata["async"] is True

    def test_node_immutable(self) -> None:
        """Test that nodes are immutable."""
        node = Node(id="test.foo", type=NodeType.FUNCTION, name="foo")
        with pytest.raises(Exception):  # FrozenInstanceError
            node.name = "bar"  # type: ignore

    def test_with_metadata(self) -> None:
        """Test creating a new node with additional metadata."""
        original = Node(id="test.foo", type=NodeType.FUNCTION, name="foo")
        enriched = original.with_metadata(docstring="test doc", version=2)
        assert enriched.metadata["docstring"] == "test doc"
        assert enriched.metadata["version"] == 2
        assert original.metadata == {}  # Original unchanged


class TestEdge:
    """Test Edge dataclass."""

    def test_create_edge(self) -> None:
        """Test creating a basic edge."""
        edge = Edge("a", "b", EdgeType.CALLS)
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.type == EdgeType.CALLS
        assert edge.metadata == {}

    def test_edge_with_metadata(self) -> None:
        """Test creating an edge with metadata."""
        edge = Edge("a", "b", EdgeType.CALLS, metadata={"line": 42})
        assert edge.metadata["line"] == 42

    def test_edge_reversed(self) -> None:
        """Test reversing an edge."""
        edge = Edge("a", "b", EdgeType.CALLS)
        rev = edge.reversed()
        assert rev.source_id == "b"
        assert rev.target_id == "a"
        assert rev.type == EdgeType.CALLS

    def test_is_self_loop(self) -> None:
        """Test detecting self-loops."""
        self_edge = Edge("a", "a", EdgeType.CALLS)
        normal_edge = Edge("a", "b", EdgeType.CALLS)
        assert self_edge.is_self_loop is True
        assert normal_edge.is_self_loop is False


class TestCodeGraph:
    """Test CodeGraph class."""

    def test_create_empty_graph(self) -> None:
        """Test creating an empty graph."""
        graph = CodeGraph()
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_node(self) -> None:
        """Test adding nodes to the graph."""
        graph = CodeGraph()
        node = Node("test.foo", NodeType.FUNCTION, "foo")
        assert graph.add_node(node) is True
        assert graph.node_count == 1
        # Adding again should return False
        assert graph.add_node(node) is False
        assert graph.node_count == 1

    def test_get_node(self) -> None:
        """Test retrieving nodes."""
        graph = CodeGraph()
        node = Node("test.foo", NodeType.FUNCTION, "foo")
        graph.add_node(node)
        retrieved = graph.get_node("test.foo")
        assert retrieved == node
        assert graph.get_node("nonexistent") is None

    def test_has_node(self) -> None:
        """Test checking node existence."""
        graph = CodeGraph()
        node = Node("test.foo", NodeType.FUNCTION, "foo")
        graph.add_node(node)
        assert graph.has_node("test.foo") is True
        assert graph.has_node("nonexistent") is False

    def test_remove_node(self) -> None:
        """Test removing nodes."""
        graph = CodeGraph()
        node = Node("test.foo", NodeType.FUNCTION, "foo")
        graph.add_node(node)
        assert graph.remove_node("test.foo") is True
        assert graph.node_count == 0
        assert graph.remove_node("test.foo") is False

    def test_add_edge(self) -> None:
        """Test adding edges."""
        graph = CodeGraph()
        node_a = Node("a", NodeType.FUNCTION, "a")
        node_b = Node("b", NodeType.FUNCTION, "b")
        graph.add_node(node_a)
        graph.add_node(node_b)

        edge = Edge("a", "b", EdgeType.CALLS)
        assert graph.add_edge(edge) is True
        assert graph.edge_count == 1
        # Adding again should return False
        assert graph.add_edge(edge) is False
        assert graph.edge_count == 1

    def test_add_edge_validates_endpoints(self) -> None:
        """Test that adding an edge validates node existence."""
        graph = CodeGraph()
        edge = Edge("a", "b", EdgeType.CALLS)
        with pytest.raises(ValueError, match="does not exist"):
            graph.add_edge(edge)

    def test_get_edge(self) -> None:
        """Test retrieving edges."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        edge = Edge("a", "b", EdgeType.CALLS)
        graph.add_edge(edge)

        retrieved = graph.get_edge("a", "b", EdgeType.CALLS)
        assert retrieved == edge
        assert graph.get_edge("a", "b", EdgeType.IMPORTS) is None

    def test_remove_edge(self) -> None:
        """Test removing edges."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        edge = Edge("a", "b", EdgeType.CALLS)
        graph.add_edge(edge)

        assert graph.remove_edge("a", "b", EdgeType.CALLS) is True
        assert graph.edge_count == 0
        assert graph.remove_edge("a", "b", EdgeType.CALLS) is False

    def test_remove_node_removes_edges(self) -> None:
        """Test that removing a node removes connected edges."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        graph.add_node(Node("c", NodeType.FUNCTION, "c"))
        graph.add_edge(Edge("a", "b", EdgeType.CALLS))
        graph.add_edge(Edge("b", "c", EdgeType.CALLS))

        graph.remove_node("b")
        assert graph.edge_count == 0

    def test_get_neighbors_outgoing(self) -> None:
        """Test getting outgoing neighbors."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        graph.add_node(Node("c", NodeType.FUNCTION, "c"))
        graph.add_edge(Edge("a", "b", EdgeType.CALLS))
        graph.add_edge(Edge("a", "c", EdgeType.CALLS))

        neighbors = graph.get_neighbors("a", direction="outgoing")
        assert len(neighbors) == 2
        neighbor_ids = {n.id for n in neighbors}
        assert neighbor_ids == {"b", "c"}

    def test_get_neighbors_incoming(self) -> None:
        """Test getting incoming neighbors."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        graph.add_node(Node("c", NodeType.FUNCTION, "c"))
        graph.add_edge(Edge("b", "a", EdgeType.CALLS))
        graph.add_edge(Edge("c", "a", EdgeType.CALLS))

        neighbors = graph.get_neighbors("a", direction="incoming")
        assert len(neighbors) == 2
        neighbor_ids = {n.id for n in neighbors}
        assert neighbor_ids == {"b", "c"}

    def test_get_neighbors_filtered_by_type(self) -> None:
        """Test filtering neighbors by edge type."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        graph.add_node(Node("c", NodeType.FUNCTION, "c"))
        graph.add_edge(Edge("a", "b", EdgeType.CALLS))
        graph.add_edge(Edge("a", "c", EdgeType.USES))

        call_neighbors = graph.get_neighbors("a", edge_type=EdgeType.CALLS)
        assert len(call_neighbors) == 1
        assert call_neighbors[0].id == "b"

    def test_nodes_iterator(self) -> None:
        """Test iterating over nodes."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.CLASS, "b"))

        all_nodes = list(graph.nodes())
        assert len(all_nodes) == 2

        functions = list(graph.nodes(node_type=NodeType.FUNCTION))
        assert len(functions) == 1
        assert functions[0].id == "a"

    def test_edges_iterator(self) -> None:
        """Test iterating over edges."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        graph.add_edge(Edge("a", "b", EdgeType.CALLS))
        graph.add_edge(Edge("a", "b", EdgeType.USES))

        all_edges = list(graph.edges())
        assert len(all_edges) == 2

        call_edges = list(graph.edges(edge_type=EdgeType.CALLS))
        assert len(call_edges) == 1

    def test_stats(self) -> None:
        """Test graph statistics."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.CLASS, "b"))
        graph.add_edge(Edge("a", "b", EdgeType.USES))

        stats = graph.stats()
        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1
        assert stats["nodes_by_type"][NodeType.FUNCTION] == 1
        assert stats["nodes_by_type"][NodeType.CLASS] == 1
        assert stats["edges_by_type"][EdgeType.USES] == 1

    def test_clear(self) -> None:
        """Test clearing the graph."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        graph.add_edge(Edge("a", "b", EdgeType.CALLS))

        graph.clear()
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_copy(self) -> None:
        """Test copying the graph."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        graph.add_node(Node("b", NodeType.FUNCTION, "b"))
        graph.add_edge(Edge("a", "b", EdgeType.CALLS))

        copy = graph.copy()
        assert copy.node_count == graph.node_count
        assert copy.edge_count == graph.edge_count
        assert copy is not graph

    def test_repr(self) -> None:
        """Test string representation."""
        graph = CodeGraph()
        graph.add_node(Node("a", NodeType.FUNCTION, "a"))
        assert "CodeGraph" in repr(graph)
        assert "nodes=1" in repr(graph)
