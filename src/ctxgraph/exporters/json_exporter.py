"""JSON export helpers for code graphs."""

from __future__ import annotations

from pathlib import Path

from ..graph import CodeGraph
from ..io import graph_to_dict, save_graph


def export_graph_json(
    graph: CodeGraph,
    output_path: Path | str,
    source_path: str | None = None,
) -> Path:
    """Write a graph export to a JSON file."""
    return save_graph(graph, output_path, source_path=source_path)
