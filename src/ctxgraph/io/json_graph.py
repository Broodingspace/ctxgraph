"""Stable JSON serialization for code graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..graph import CodeGraph, Edge, EdgeType, Node, NodeType, SourceLocation


GRAPH_FORMAT_VERSION = "1"


def _node_to_dict(node: Node) -> dict[str, Any]:
    """Serialize a node to a JSON-compatible dictionary."""
    location = None
    if node.location is not None:
        location = {
            "file_path": node.location.file_path,
            "line_start": node.location.line_start,
            "line_end": node.location.line_end,
            "column_start": node.location.column_start,
            "column_end": node.location.column_end,
        }

    return {
        "id": node.id,
        "type": node.type.name.lower(),
        "name": node.name,
        "location": location,
        "metadata": node.metadata,
    }


def _edge_to_dict(edge: Edge) -> dict[str, Any]:
    """Serialize an edge to a JSON-compatible dictionary."""
    return {
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "type": edge.type.name.lower(),
        "metadata": edge.metadata,
    }


def graph_to_dict(graph: CodeGraph, source_path: str | None = None) -> dict[str, Any]:
    """Serialize a graph into a stable dictionary structure."""
    stats = graph.stats()
    nodes_by_type = {
        node_type.name.lower(): count for node_type, count in stats["nodes_by_type"].items()
    }
    edges_by_type = {
        edge_type.name.lower(): count for edge_type, count in stats["edges_by_type"].items()
    }

    return {
        "format": "ctxgraph-json",
        "version": GRAPH_FORMAT_VERSION,
        "source_path": source_path,
        "summary": {
            "total_nodes": stats["total_nodes"],
            "total_edges": stats["total_edges"],
            "nodes_by_type": nodes_by_type,
            "edges_by_type": edges_by_type,
        },
        "nodes": [_node_to_dict(node) for node in sorted(graph.nodes(), key=lambda item: item.id)],
        "edges": sorted(
            (_edge_to_dict(edge) for edge in graph.edges()),
            key=lambda item: (item["source_id"], item["target_id"], item["type"]),
        ),
    }


def _location_from_dict(payload: dict[str, Any] | None) -> SourceLocation | None:
    """Deserialize an optional source location payload."""
    if payload is None:
        return None

    return SourceLocation(
        file_path=payload["file_path"],
        line_start=payload["line_start"],
        line_end=payload["line_end"],
        column_start=payload.get("column_start"),
        column_end=payload.get("column_end"),
    )


def graph_from_dict(payload: dict[str, Any]) -> CodeGraph:
    """Deserialize a graph from a dictionary payload."""
    if payload.get("format") != "ctxgraph-json":
        raise ValueError("Unsupported graph format")
    if payload.get("version") != GRAPH_FORMAT_VERSION:
        raise ValueError(f"Unsupported graph version: {payload.get('version')}")

    graph = CodeGraph()

    for node_data in payload.get("nodes", []):
        node = Node(
            id=node_data["id"],
            type=NodeType[node_data["type"].upper()],
            name=node_data["name"],
            location=_location_from_dict(node_data.get("location")),
            metadata=dict(node_data.get("metadata", {})),
        )
        graph.add_node(node)

    for edge_data in payload.get("edges", []):
        edge = Edge(
            source_id=edge_data["source_id"],
            target_id=edge_data["target_id"],
            type=EdgeType[edge_data["type"].upper()],
            metadata=dict(edge_data.get("metadata", {})),
        )
        graph.add_edge(edge)

    return graph


def save_graph(
    graph: CodeGraph,
    output_path: Path | str,
    source_path: str | None = None,
) -> Path:
    """Write a serialized graph to disk."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(graph_to_dict(graph, source_path=source_path), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


def load_graph(input_path: Path | str) -> CodeGraph:
    """Load a serialized graph from disk."""
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return graph_from_dict(payload)
