"""Tests for the ctxgraph GitHub Action helper script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from ctxgraph import build_graph
from ctxgraph.query import QueryEngine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"
SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "github_action.py"

_SPEC = importlib.util.spec_from_file_location("ctxgraph_github_action", SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

ChangedLineRange = _MODULE.ChangedLineRange
ChangedFile = _MODULE.ChangedFile
build_impact_entries = _MODULE.build_impact_entries
format_markdown_report = _MODULE.format_markdown_report
map_changed_files_to_nodes = _MODULE.map_changed_files_to_nodes
parse_changed_files = _MODULE.parse_changed_files


def test_parse_changed_files_extracts_python_ranges(tmp_path: Path) -> None:
    """Diff parsing should collect changed Python files and line ranges."""
    repo_root = tmp_path
    diff = "\n".join(
        [
            "diff --git a/pkg/example.py b/pkg/example.py",
            "--- a/pkg/example.py",
            "+++ b/pkg/example.py",
            "@@ -10,0 +11,3 @@",
            "+print('x')",
        ]
    )

    changed = parse_changed_files(diff, repo_root)

    assert len(changed) == 1
    assert changed[0].path == (repo_root / "pkg" / "example.py").resolve()
    assert changed[0].ranges == (ChangedLineRange(start=11, end=13),)


def test_map_changed_files_to_nodes_matches_source_ranges() -> None:
    """Changed file mapping should select overlapping nodes."""
    graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
    target = next(node for node in graph.nodes() if node.name == "helper_function")
    assert target.location is not None

    changed = [
        ChangedFile(
            path=Path(target.location.file_path).resolve(),
            ranges=(ChangedLineRange(target.location.line_start, target.location.line_end),),
        )
    ]

    mapped = map_changed_files_to_nodes(list(graph.nodes()), changed)

    assert any(node.id == target.id for node in mapped)


def test_build_impact_entries_and_markdown_report() -> None:
    """Impact entries should produce a stable markdown report."""
    graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
    engine = QueryEngine(graph)
    target = next(node for node in graph.nodes() if node.name == "BaseModel")
    assert target.location is not None
    changed = [
        ChangedFile(
            path=Path(target.location.file_path).resolve(),
            ranges=(ChangedLineRange(target.location.line_start, target.location.line_end),),
        )
    ]

    entries = build_impact_entries(list(graph.nodes()), engine, changed, max_depth=2, max_callers=3)
    report = format_markdown_report(entries, changed)

    assert entries
    assert "ctxgraph" in report
    assert "Changed symbols" in report
    assert target.id in report
