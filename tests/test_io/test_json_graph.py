"""Tests for graph JSON serialization."""

from __future__ import annotations

from pathlib import Path

from ctxgraph import build_graph, load_graph, save_graph

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


def test_save_and_load_graph_round_trip(tmp_path: Path) -> None:
    """Serialized graphs should load back with stable counts and symbols."""
    graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
    output_path = tmp_path / "graph.json"

    saved_path = save_graph(graph, output_path, source_path=str(SAMPLE_PROJECT))
    loaded_graph = load_graph(saved_path)

    assert loaded_graph.node_count == graph.node_count
    assert loaded_graph.edge_count == graph.edge_count
    assert loaded_graph.has_node("sample_project.models.User")
    assert loaded_graph.has_node("sample_project.utils.helper_function")
