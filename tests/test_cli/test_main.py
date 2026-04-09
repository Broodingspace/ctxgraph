"""Tests for the ctxgraph CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctxgraph import build_graph, save_graph
from ctxgraph.cli.main import main

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


def _find_symbol_id(name: str) -> str:
    """Find a symbol ID by name in the sample project."""
    graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
    for node in graph.nodes():
        if node.name == name:
            return node.id
    raise AssertionError(f"Expected symbol named {name}")


def test_build_command_prints_summary(capsys: pytest.CaptureFixture[str]) -> None:
    """The build command should print graph summary statistics."""
    exit_code = main(["build", str(SAMPLE_PROJECT)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Repository:" in captured.out
    assert "Nodes:" in captured.out
    assert "Edges:" in captured.out


def test_build_command_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    """The build command should support JSON summary output."""
    exit_code = main(["build", str(SAMPLE_PROJECT), "--json"])
    captured = capsys.readouterr()

    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["total_nodes"] > 0
    assert payload["total_edges"] > 0


def test_inspect_command_prints_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    """The inspect command should print node details."""
    symbol_id = _find_symbol_id("User")
    exit_code = main(["inspect", "--repo", str(SAMPLE_PROJECT), symbol_id])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"ID: {symbol_id}" in captured.out
    assert "Type: class" in captured.out
    assert "Metadata:" in captured.out


def test_deps_command_supports_reverse(capsys: pytest.CaptureFixture[str]) -> None:
    """The deps command should print reverse dependencies."""
    symbol_id = _find_symbol_id("BaseModel")
    exit_code = main(["deps", "--repo", str(SAMPLE_PROJECT), "--reverse", symbol_id])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Reverse dependencies for" in captured.out


def test_blast_radius_command_groups_by_distance(capsys: pytest.CaptureFixture[str]) -> None:
    """The blast-radius command should group nodes by hop count."""
    symbol_id = _find_symbol_id("User")
    exit_code = main(
        ["blast-radius", "--repo", str(SAMPLE_PROJECT), "--depth", "2", "--direction", "both", symbol_id]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Blast radius for" in captured.out


def test_trace_command_prints_path_or_no_path(capsys: pytest.CaptureFixture[str]) -> None:
    """The trace command should handle empty paths gracefully."""
    exit_code = main(
        [
            "trace",
            "--repo",
            str(SAMPLE_PROJECT),
            "sample_project.models.User",
            "sample_project.utils.helper_function",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.startswith("No path found") or "Path from" in captured.out


def test_export_command_writes_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The export command should write a JSON file."""
    output_path = tmp_path / "graph.json"
    exit_code = main(["export", str(SAMPLE_PROJECT), "--out", str(output_path)])
    captured = capsys.readouterr()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "Exported json graph" in captured.out
    assert payload["summary"]["total_nodes"] > 0
    assert payload["summary"]["total_edges"] > 0


def test_load_command_reads_serialized_graph(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The load command should read a serialized graph summary."""
    graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
    graph_path = save_graph(graph, tmp_path / "graph.json", source_path=str(SAMPLE_PROJECT))

    exit_code = main(["load", str(graph_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Graph file:" in captured.out
    assert "Nodes:" in captured.out


def test_inspect_command_supports_graph_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The inspect command should query a saved graph without rebuilding."""
    graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
    graph_path = save_graph(graph, tmp_path / "graph.json", source_path=str(SAMPLE_PROJECT))
    symbol_id = _find_symbol_id("User")

    exit_code = main(["inspect", "--graph-file", str(graph_path), symbol_id])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Source:" in captured.out
    assert f"ID: {symbol_id}" in captured.out


def test_missing_repo_returns_error(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI should report missing repository paths cleanly."""
    exit_code = main(["build", "does-not-exist"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Error:" in captured.err


def test_missing_graph_file_returns_error(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI should report missing serialized graph files cleanly."""
    exit_code = main(["load", "does-not-exist.json"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Error:" in captured.err
