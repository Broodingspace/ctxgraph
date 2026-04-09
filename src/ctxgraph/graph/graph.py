"""Core graph data structure for representing code relationships.

The CodeGraph class provides the primary interface for building and querying
the code graph. It maintains efficient indices for both forward and reverse
edge traversal.
"""

from collections import defaultdict
from typing import Iterator, Self

from .edge import Edge
from .node import Node
from .types import EdgeType, NodeType


class CodeGraph:
    """A directed graph representing code structure and relationships.

    The graph maintains nodes (code entities) and edges (relationships) with
    efficient indices for querying. Both forward and reverse edge indices are
    maintained for bidirectional traversal.

    The graph enforces:
    - Node uniqueness by ID
    - Edge endpoints must reference existing nodes
    - No duplicate edges (same source, target, and type)

    Attributes:
        _nodes: Map from node ID to Node object.
        _edges: Set of all edges in the graph.
        _outgoing: Map from source_id to list of outgoing edges.
        _incoming: Map from target_id to list of incoming edges.

    Examples:
        >>> graph = CodeGraph()
        >>> mod = Node("myapp.utils", NodeType.MODULE, "utils")
        >>> func = Node("myapp.utils.helper", NodeType.FUNCTION, "helper")
        >>> graph.add_node(mod)
        >>> graph.add_node(func)
        >>> graph.add_edge(Edge("myapp.utils", "myapp.utils.helper", EdgeType.DEFINES))
        >>> graph.node_count
        2
        >>> graph.edge_count
        1
    """

    def __init__(self) -> None:
        """Initialize an empty code graph."""
        self._nodes: dict[str, Node] = {}
        self._edges: set[Edge] = set()

        # Adjacency indices for efficient traversal
        # Key: node_id, Value: list of edges
        self._outgoing: dict[str, list[Edge]] = defaultdict(list)
        self._incoming: dict[str, list[Edge]] = defaultdict(list)

    # ==================== Node Operations ====================

    def add_node(self, node: Node) -> bool:
        """Add a node to the graph.

        Args:
            node: The node to add.

        Returns:
            True if the node was added, False if it already existed.

        Raises:
            ValueError: If node.id is empty.

        Examples:
            >>> graph = CodeGraph()
            >>> node = Node("test.foo", NodeType.FUNCTION, "foo")
            >>> graph.add_node(node)
            True
            >>> graph.add_node(node)  # Adding again
            False
        """
        if node.id in self._nodes:
            return False
        self._nodes[node.id] = node
        return True

    def get_node(self, node_id: str) -> Node | None:
        """Retrieve a node by its ID.

        Args:
            node_id: The unique identifier of the node.

        Returns:
            The Node if found, None otherwise.

        Examples:
            >>> graph = CodeGraph()
            >>> node = Node("test.foo", NodeType.FUNCTION, "foo")
            >>> graph.add_node(node)
            True
            >>> graph.get_node("test.foo")
            Node(id='test.foo', ...)
            >>> graph.get_node("nonexistent")
            None
        """
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists in the graph.

        Args:
            node_id: The unique identifier to check.

        Returns:
            True if the node exists, False otherwise.
        """
        return node_id in self._nodes

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its connected edges from the graph.

        Args:
            node_id: The ID of the node to remove.

        Returns:
            True if the node was removed, False if it didn't exist.

        Examples:
            >>> graph = CodeGraph()
            >>> node = Node("test.foo", NodeType.FUNCTION, "foo")
            >>> graph.add_node(node)
            True
            >>> graph.remove_node("test.foo")
            True
            >>> graph.has_node("test.foo")
            False
        """
        if node_id not in self._nodes:
            return False

        # Remove all edges connected to this node
        edges_to_remove = list(self._outgoing.get(node_id, [])) + list(
            self._incoming.get(node_id, [])
        )
        for edge in edges_to_remove:
            self.remove_edge(edge.source_id, edge.target_id, edge.type)

        # Remove the node itself
        del self._nodes[node_id]
        return True

    def nodes(
        self, node_type: NodeType | None = None, name_filter: str | None = None
    ) -> Iterator[Node]:
        """Iterate over nodes, optionally filtered by type or name.

        Args:
            node_type: If provided, only yield nodes of this type.
            name_filter: If provided, only yield nodes whose name contains this substring.

        Yields:
            Nodes matching the filter criteria.

        Examples:
            >>> graph = CodeGraph()
            >>> graph.add_node(Node("a", NodeType.FUNCTION, "foo"))
            True
            >>> graph.add_node(Node("b", NodeType.CLASS, "Bar"))
            True
            >>> list(graph.nodes(node_type=NodeType.FUNCTION))
            [Node(id='a', ...)]
        """
        for node in self._nodes.values():
            if node_type is not None and node.type != node_type:
                continue
            if name_filter is not None and name_filter not in node.name:
                continue
            yield node

    # ==================== Edge Operations ====================

    def add_edge(self, edge: Edge) -> bool:
        """Add an edge to the graph.

        Args:
            edge: The edge to add.

        Returns:
            True if the edge was added, False if it already existed.

        Raises:
            ValueError: If either endpoint node doesn't exist in the graph.

        Examples:
            >>> graph = CodeGraph()
            >>> graph.add_node(Node("a", NodeType.FUNCTION, "a"))
            True
            >>> graph.add_node(Node("b", NodeType.FUNCTION, "b"))
            True
            >>> edge = Edge("a", "b", EdgeType.CALLS)
            >>> graph.add_edge(edge)
            True
            >>> graph.add_edge(edge)  # Adding again
            False
        """
        # Validate that both endpoints exist
        if not self.has_node(edge.source_id):
            raise ValueError(f"Source node '{edge.source_id}' does not exist in graph")
        if not self.has_node(edge.target_id):
            raise ValueError(f"Target node '{edge.target_id}' does not exist in graph")

        # Check if edge already exists (by identity, since Edge is frozen/hashable)
        if edge in self._edges:
            return False

        # Add to edge set and indices
        self._edges.add(edge)
        self._outgoing[edge.source_id].append(edge)
        self._incoming[edge.target_id].append(edge)
        return True

    def get_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> Edge | None:
        """Retrieve a specific edge by its endpoints and type.

        Args:
            source_id: The source node ID.
            target_id: The target node ID.
            edge_type: The type of edge.

        Returns:
            The Edge if found, None otherwise.

        Examples:
            >>> graph = CodeGraph()
            >>> graph.add_node(Node("a", NodeType.FUNCTION, "a"))
            True
            >>> graph.add_node(Node("b", NodeType.FUNCTION, "b"))
            True
            >>> graph.add_edge(Edge("a", "b", EdgeType.CALLS))
            True
            >>> graph.get_edge("a", "b", EdgeType.CALLS)
            Edge(source_id='a', target_id='b', type=<EdgeType.CALLS: 4>)
        """
        for edge in self._outgoing.get(source_id, []):
            if edge.target_id == target_id and edge.type == edge_type:
                return edge
        return None

    def has_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        """Check if a specific edge exists.

        Args:
            source_id: The source node ID.
            target_id: The target node ID.
            edge_type: The type of edge.

        Returns:
            True if the edge exists, False otherwise.
        """
        return self.get_edge(source_id, target_id, edge_type) is not None

    def remove_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        """Remove a specific edge from the graph.

        Args:
            source_id: The source node ID.
            target_id: The target node ID.
            edge_type: The type of edge to remove.

        Returns:
            True if the edge was removed, False if it didn't exist.

        Examples:
            >>> graph = CodeGraph()
            >>> graph.add_node(Node("a", NodeType.FUNCTION, "a"))
            True
            >>> graph.add_node(Node("b", NodeType.FUNCTION, "b"))
            True
            >>> graph.add_edge(Edge("a", "b", EdgeType.CALLS))
            True
            >>> graph.remove_edge("a", "b", EdgeType.CALLS)
            True
            >>> graph.has_edge("a", "b", EdgeType.CALLS)
            False
        """
        edge = self.get_edge(source_id, target_id, edge_type)
        if edge is None:
            return False

        # Remove from all indices
        self._edges.discard(edge)
        self._outgoing[source_id].remove(edge)
        self._incoming[target_id].remove(edge)

        # Clean up empty lists to save memory
        if not self._outgoing[source_id]:
            del self._outgoing[source_id]
        if not self._incoming[target_id]:
            del self._incoming[target_id]

        return True

    def edges(
        self, edge_type: EdgeType | None = None, source_id: str | None = None
    ) -> Iterator[Edge]:
        """Iterate over edges, optionally filtered.

        Args:
            edge_type: If provided, only yield edges of this type.
            source_id: If provided, only yield edges from this source node.

        Yields:
            Edges matching the filter criteria.

        Examples:
            >>> graph = CodeGraph()
            >>> graph.add_node(Node("a", NodeType.FUNCTION, "a"))
            True
            >>> graph.add_node(Node("b", NodeType.FUNCTION, "b"))
            True
            >>> graph.add_edge(Edge("a", "b", EdgeType.CALLS))
            True
            >>> list(graph.edges(edge_type=EdgeType.CALLS))
            [Edge(...)]
        """
        # If source_id is specified, use the outgoing index
        if source_id is not None:
            edges_to_check = self._outgoing.get(source_id, [])
        else:
            edges_to_check = self._edges

        for edge in edges_to_check:
            if edge_type is not None and edge.type != edge_type:
                continue
            yield edge

    # ==================== Traversal Operations ====================

    def get_neighbors(
        self,
        node_id: str,
        edge_type: EdgeType | None = None,
        direction: str = "outgoing",
    ) -> list[Node]:
        """Get neighboring nodes connected by edges.

        Args:
            node_id: The node to start from.
            edge_type: If provided, only follow edges of this type.
            direction: Either "outgoing" (default), "incoming", or "both".

        Returns:
            List of neighboring nodes.

        Raises:
            ValueError: If direction is invalid or node doesn't exist.

        Examples:
            >>> graph = CodeGraph()
            >>> graph.add_node(Node("a", NodeType.FUNCTION, "a"))
            True
            >>> graph.add_node(Node("b", NodeType.FUNCTION, "b"))
            True
            >>> graph.add_edge(Edge("a", "b", EdgeType.CALLS))
            True
            >>> neighbors = graph.get_neighbors("a", direction="outgoing")
            >>> len(neighbors)
            1
            >>> neighbors[0].id
            'b'
        """
        if not self.has_node(node_id):
            raise ValueError(f"Node '{node_id}' does not exist in graph")

        if direction not in ("outgoing", "incoming", "both"):
            raise ValueError(f"Invalid direction: {direction}")

        neighbor_ids: set[str] = set()

        if direction in ("outgoing", "both"):
            for edge in self._outgoing.get(node_id, []):
                if edge_type is None or edge.type == edge_type:
                    neighbor_ids.add(edge.target_id)

        if direction in ("incoming", "both"):
            for edge in self._incoming.get(node_id, []):
                if edge_type is None or edge.type == edge_type:
                    neighbor_ids.add(edge.source_id)

        return [self._nodes[nid] for nid in neighbor_ids]

    def get_outgoing_edges(self, node_id: str) -> list[Edge]:
        """Get all outgoing edges from a node.

        Args:
            node_id: The source node ID.

        Returns:
            List of outgoing edges.
        """
        return list(self._outgoing.get(node_id, []))

    def get_incoming_edges(self, node_id: str) -> list[Edge]:
        """Get all incoming edges to a node.

        Args:
            node_id: The target node ID.

        Returns:
            List of incoming edges.
        """
        return list(self._incoming.get(node_id, []))

    # ==================== Graph Statistics ====================

    @property
    def node_count(self) -> int:
        """Return the total number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Return the total number of edges in the graph."""
        return len(self._edges)

    def stats(self) -> dict[str, int | dict[str, int]]:
        """Compute graph statistics.

        Returns:
            Dictionary with statistics including node/edge counts and breakdowns by type.

        Examples:
            >>> graph = CodeGraph()
            >>> graph.add_node(Node("a", NodeType.FUNCTION, "a"))
            True
            >>> graph.add_node(Node("b", NodeType.CLASS, "b"))
            True
            >>> stats = graph.stats()
            >>> stats["total_nodes"]
            2
            >>> stats["nodes_by_type"][NodeType.FUNCTION]
            1
        """
        node_counts: dict[NodeType, int] = defaultdict(int)
        edge_counts: dict[EdgeType, int] = defaultdict(int)

        for node in self._nodes.values():
            node_counts[node.type] += 1

        for edge in self._edges:
            edge_counts[edge.type] += 1

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "nodes_by_type": dict(node_counts),
            "edges_by_type": dict(edge_counts),
        }

    # ==================== Utility Methods ====================

    def clear(self) -> None:
        """Remove all nodes and edges from the graph."""
        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()

    def copy(self) -> Self:
        """Create a shallow copy of the graph.

        Returns:
            A new CodeGraph with the same nodes and edges.

        Note:
            Nodes and edges are immutable, so shallow copy is safe.
        """
        new_graph = CodeGraph()
        for node in self._nodes.values():
            new_graph.add_node(node)
        for edge in self._edges:
            new_graph.add_edge(edge)
        return new_graph

    def __repr__(self) -> str:
        """Return a string representation of the graph."""
        return f"CodeGraph(nodes={self.node_count}, edges={self.edge_count})"
