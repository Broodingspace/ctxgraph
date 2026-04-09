"""Query engine for analyzing code graphs.

This module provides high-level query APIs for extracting insights from
code graphs, including dependency analysis, impact assessment, and context
extraction for AI systems.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from ..graph import CodeGraph, EdgeType, Node, NodeType


@dataclass
class DependencyResult:
    """Result of a dependency query.

    Attributes:
        node: The queried node.
        dependencies: Nodes that this node depends on.
        dependency_types: Map from dependency node ID to list of edge types.
    """

    node: Node
    dependencies: list[Node] = field(default_factory=list)
    dependency_types: dict[str, list[EdgeType]] = field(default_factory=dict)

    @property
    def count(self) -> int:
        """Return the number of dependencies."""
        return len(self.dependencies)


@dataclass
class BlastRadiusResult:
    """Result of a blast radius analysis.

    Attributes:
        origin: The origin node.
        affected_nodes: Nodes that could be affected by changes to origin.
        distances: Map from node ID to distance from origin.
        paths: Map from node ID to shortest path from origin.
    """

    origin: Node
    affected_nodes: list[Node] = field(default_factory=list)
    distances: dict[str, int] = field(default_factory=dict)
    paths: dict[str, list[str]] = field(default_factory=dict)

    @property
    def count(self) -> int:
        """Return the number of affected nodes."""
        return len(self.affected_nodes)

    def nodes_at_distance(self, distance: int) -> list[Node]:
        """Get nodes at a specific distance from origin.

        Args:
            distance: Distance from origin.

        Returns:
            List of nodes at that distance.
        """
        return [n for n in self.affected_nodes if self.distances[n.id] == distance]


@dataclass
class PathResult:
    """Result of a path finding query.

    Attributes:
        source: The source node.
        target: The target node.
        path: List of node IDs from source to target (inclusive).
        edges: List of edge types along the path.
        length: Length of the path (number of edges).
    """

    source: Node
    target: Node
    path: list[str] = field(default_factory=list)
    edges: list[EdgeType] = field(default_factory=list)

    @property
    def length(self) -> int:
        """Return the path length (number of edges)."""
        return len(self.edges)

    @property
    def exists(self) -> bool:
        """Return whether a path was found."""
        return len(self.path) > 0


@dataclass
class ContextResult:
    """Result of a context extraction query.

    Attributes:
        origin: The origin node.
        context_nodes: Nodes in the context (including origin).
        layers: Map from distance to list of nodes at that distance.
        total_size: Total number of nodes in context.
    """

    origin: Node
    context_nodes: list[Node] = field(default_factory=list)
    layers: dict[int, list[Node]] = field(default_factory=dict)

    @property
    def total_size(self) -> int:
        """Return the total number of nodes in context."""
        return len(self.context_nodes)

    def get_files(self) -> set[str]:
        """Get unique file paths in the context.

        Returns:
            Set of file paths.
        """
        files = set()
        for node in self.context_nodes:
            if node.file_path:
                files.add(node.file_path)
        return files


class QueryEngine:
    """High-level query engine for code graphs.

    This class provides APIs for analyzing code graphs to answer questions
    about dependencies, impact, and relationships. Designed for AI tooling,
    code analysis, and developer productivity tools.
    """

    def __init__(self, graph: CodeGraph) -> None:
        """Initialize query engine.

        Args:
            graph: The code graph to query.
        """
        self.graph = graph

    # ==================== Dependency Queries ====================

    def get_dependencies(
        self,
        node_id: str,
        edge_types: list[EdgeType] | None = None,
        transitive: bool = False,
    ) -> DependencyResult:
        """Get dependencies of a node.

        Returns all nodes that the given node depends on, optionally filtered
        by edge type. Can return direct dependencies or transitive closure.

        Args:
            node_id: ID of the node to query.
            edge_types: Optional list of edge types to follow (default: all).
            transitive: If True, return transitive closure of dependencies.

        Returns:
            DependencyResult with dependencies and metadata.

        Raises:
            ValueError: If node does not exist.

        Examples:
            >>> engine = QueryEngine(graph)
            >>> result = engine.get_dependencies("myapp.utils.helper")
            >>> result.count
            3
            >>> # Get only import dependencies
            >>> result = engine.get_dependencies(
            ...     "myapp.main",
            ...     edge_types=[EdgeType.IMPORTS]
            ... )
        """
        node = self.graph.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")

        if not transitive:
            # Direct dependencies only
            dependencies = []
            dependency_types: dict[str, list[EdgeType]] = {}

            for edge in self.graph.get_outgoing_edges(node_id):
                if edge_types and edge.type not in edge_types:
                    continue

                target = self.graph.get_node(edge.target_id)
                if target:
                    dependencies.append(target)
                    if edge.target_id not in dependency_types:
                        dependency_types[edge.target_id] = []
                    dependency_types[edge.target_id].append(edge.type)

            return DependencyResult(
                node=node,
                dependencies=dependencies,
                dependency_types=dependency_types,
            )
        else:
            # Transitive dependencies (BFS)
            visited = set()
            dependencies = []
            dependency_types: dict[str, list[EdgeType]] = {}
            queue = deque([node_id])

            while queue:
                current_id = queue.popleft()
                if current_id in visited:
                    continue
                visited.add(current_id)

                for edge in self.graph.get_outgoing_edges(current_id):
                    if edge_types and edge.type not in edge_types:
                        continue

                    target_id = edge.target_id
                    if target_id not in visited:
                        queue.append(target_id)

                        target = self.graph.get_node(target_id)
                        if target and target_id != node_id:
                            dependencies.append(target)
                            if target_id not in dependency_types:
                                dependency_types[target_id] = []
                            dependency_types[target_id].append(edge.type)

            return DependencyResult(
                node=node,
                dependencies=dependencies,
                dependency_types=dependency_types,
            )

    def get_reverse_dependencies(
        self,
        node_id: str,
        edge_types: list[EdgeType] | None = None,
        transitive: bool = False,
    ) -> DependencyResult:
        """Get reverse dependencies (dependents) of a node.

        Returns all nodes that depend on the given node. This answers
        "what would break if I change this node?"

        Args:
            node_id: ID of the node to query.
            edge_types: Optional list of edge types to follow (default: all).
            transitive: If True, return transitive closure of dependents.

        Returns:
            DependencyResult with reverse dependencies.

        Raises:
            ValueError: If node does not exist.

        Examples:
            >>> engine = QueryEngine(graph)
            >>> result = engine.get_reverse_dependencies("myapp.models.User")
            >>> print(f"{result.count} modules depend on User")
            5 modules depend on User
        """
        node = self.graph.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")

        if not transitive:
            # Direct dependents only
            dependents = []
            dependency_types: dict[str, list[EdgeType]] = {}

            for edge in self.graph.get_incoming_edges(node_id):
                if edge_types and edge.type not in edge_types:
                    continue

                source = self.graph.get_node(edge.source_id)
                if source:
                    dependents.append(source)
                    if edge.source_id not in dependency_types:
                        dependency_types[edge.source_id] = []
                    dependency_types[edge.source_id].append(edge.type)

            return DependencyResult(
                node=node,
                dependencies=dependents,
                dependency_types=dependency_types,
            )
        else:
            # Transitive dependents (BFS backwards)
            visited = set()
            dependents = []
            dependency_types: dict[str, list[EdgeType]] = {}
            queue = deque([node_id])

            while queue:
                current_id = queue.popleft()
                if current_id in visited:
                    continue
                visited.add(current_id)

                for edge in self.graph.get_incoming_edges(current_id):
                    if edge_types and edge.type not in edge_types:
                        continue

                    source_id = edge.source_id
                    if source_id not in visited:
                        queue.append(source_id)

                        source = self.graph.get_node(source_id)
                        if source and source_id != node_id:
                            dependents.append(source)
                            if source_id not in dependency_types:
                                dependency_types[source_id] = []
                            dependency_types[source_id].append(edge.type)

            return DependencyResult(
                node=node,
                dependencies=dependents,
                dependency_types=dependency_types,
            )

    # ==================== Impact Analysis ====================

    def find_blast_radius(
        self,
        node_id: str,
        max_depth: int = 2,
        edge_types: list[EdgeType] | None = None,
        direction: str = "outgoing",
    ) -> BlastRadiusResult:
        """Find the blast radius of a node.

        Returns all nodes within max_depth hops that could be affected
        by changes to the given node. This is crucial for impact analysis.

        Args:
            node_id: ID of the node to analyze.
            max_depth: Maximum distance to traverse (default: 2).
            edge_types: Optional list of edge types to follow.
            direction: "outgoing" (dependencies), "incoming" (dependents),
                      or "both" (default: "outgoing").

        Returns:
            BlastRadiusResult with affected nodes and distances.

        Raises:
            ValueError: If node does not exist or direction is invalid.

        Examples:
            >>> engine = QueryEngine(graph)
            >>> result = engine.find_blast_radius("myapp.utils", max_depth=2)
            >>> print(f"Blast radius: {result.count} nodes")
            >>> for node in result.nodes_at_distance(1):
            ...     print(f"  Direct impact: {node.id}")
        """
        node = self.graph.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")

        if direction not in ("outgoing", "incoming", "both"):
            raise ValueError(f"Invalid direction: {direction}")

        # BFS with distance tracking
        visited = {node_id}
        distances = {node_id: 0}
        paths: dict[str, list[str]] = {node_id: [node_id]}
        queue = deque([(node_id, 0)])
        affected_nodes = []

        while queue:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            # Get neighbors based on direction
            edges = []
            if direction in ("outgoing", "both"):
                edges.extend(self.graph.get_outgoing_edges(current_id))
            if direction in ("incoming", "both"):
                edges.extend(self.graph.get_incoming_edges(current_id))

            for edge in edges:
                if edge_types and edge.type not in edge_types:
                    continue

                # Determine neighbor based on direction
                if edge.source_id == current_id:
                    neighbor_id = edge.target_id
                else:
                    neighbor_id = edge.source_id

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    distances[neighbor_id] = depth + 1
                    paths[neighbor_id] = paths[current_id] + [neighbor_id]
                    queue.append((neighbor_id, depth + 1))

                    neighbor = self.graph.get_node(neighbor_id)
                    if neighbor:
                        affected_nodes.append(neighbor)

        return BlastRadiusResult(
            origin=node,
            affected_nodes=affected_nodes,
            distances=distances,
            paths=paths,
        )

    # ==================== Path Finding ====================

    def trace_path(
        self,
        source_id: str,
        target_id: str,
        edge_types: list[EdgeType] | None = None,
    ) -> PathResult:
        """Find a path between two nodes.

        Uses BFS to find the shortest path between source and target nodes.
        Useful for understanding how two parts of code are connected.

        Args:
            source_id: ID of the source node.
            target_id: ID of the target node.
            edge_types: Optional list of edge types to follow.

        Returns:
            PathResult with path information (empty if no path exists).

        Raises:
            ValueError: If either node does not exist.

        Examples:
            >>> engine = QueryEngine(graph)
            >>> result = engine.trace_path("myapp.main", "myapp.utils.helper")
            >>> if result.exists:
            ...     print(f"Path length: {result.length}")
            ...     print(" -> ".join(result.path))
        """
        source = self.graph.get_node(source_id)
        target = self.graph.get_node(target_id)

        if not source:
            raise ValueError(f"Source node '{source_id}' not found")
        if not target:
            raise ValueError(f"Target node '{target_id}' not found")

        # BFS to find shortest path
        visited = {source_id}
        queue = deque([(source_id, [source_id], [])])

        while queue:
            current_id, path, edges = queue.popleft()

            if current_id == target_id:
                # Found the target
                return PathResult(
                    source=source,
                    target=target,
                    path=path,
                    edges=edges,
                )

            # Explore neighbors (only outgoing edges for path finding)
            for edge in self.graph.get_outgoing_edges(current_id):
                if edge_types and edge.type not in edge_types:
                    continue

                neighbor_id = edge.target_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((
                        neighbor_id,
                        path + [neighbor_id],
                        edges + [edge.type],
                    ))

        # No path found
        return PathResult(source=source, target=target)

    # ==================== Context Extraction ====================

    def get_related_context(
        self,
        node_id: str,
        radius: int = 2,
        edge_types: list[EdgeType] | None = None,
        node_filter: Callable[[Node], bool] | None = None,
    ) -> ContextResult:
        """Get related context around a node.

        Extracts nodes within a given radius of the origin node. This is
        crucial for building context windows for LLMs or understanding
        the local structure around a code entity.

        Args:
            node_id: ID of the origin node.
            radius: Maximum distance to include (default: 2).
            edge_types: Optional list of edge types to follow.
            node_filter: Optional function to filter nodes.

        Returns:
            ContextResult with context nodes organized by distance.

        Raises:
            ValueError: If node does not exist.

        Examples:
            >>> engine = QueryEngine(graph)
            >>> # Get context for a function
            >>> result = engine.get_related_context("myapp.utils.helper", radius=2)
            >>> print(f"Context size: {result.total_size} nodes")
            >>> print(f"Files involved: {len(result.get_files())}")
            >>>
            >>> # Filter to only include functions/classes
            >>> result = engine.get_related_context(
            ...     "myapp.utils.helper",
            ...     node_filter=lambda n: n.type in (NodeType.FUNCTION, NodeType.CLASS)
            ... )
        """
        node = self.graph.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found")

        # BFS with distance tracking (bidirectional: both incoming and outgoing)
        visited = {node_id}
        layers: dict[int, list[Node]] = {0: [node]}
        queue = deque([(node_id, 0)])
        context_nodes = [node]

        while queue:
            current_id, depth = queue.popleft()

            if depth >= radius:
                continue

            # Get all neighbors (both directions for context)
            edges = []
            edges.extend(self.graph.get_outgoing_edges(current_id))
            edges.extend(self.graph.get_incoming_edges(current_id))

            for edge in edges:
                if edge_types and edge.type not in edge_types:
                    continue

                # Determine neighbor
                if edge.source_id == current_id:
                    neighbor_id = edge.target_id
                else:
                    neighbor_id = edge.source_id

                if neighbor_id not in visited:
                    visited.add(neighbor_id)

                    neighbor = self.graph.get_node(neighbor_id)
                    if neighbor:
                        # Apply filter if provided
                        if node_filter and not node_filter(neighbor):
                            continue

                        next_depth = depth + 1
                        if next_depth not in layers:
                            layers[next_depth] = []
                        layers[next_depth].append(neighbor)
                        context_nodes.append(neighbor)

                        queue.append((neighbor_id, next_depth))

        return ContextResult(
            origin=node,
            context_nodes=context_nodes,
            layers=layers,
        )
