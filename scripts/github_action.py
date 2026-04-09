"""Proof-of-concept GitHub Action for ctxgraph PR impact reports."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ctxgraph import QueryEngine, build_graph
from ctxgraph.graph import Node, NodeType


def log(message: str) -> None:
    """Print a normal log line."""
    print(message)


def group(title: str) -> None:
    """Start a GitHub Actions log group."""
    print(f"::group::{title}")


def endgroup() -> None:
    """End a GitHub Actions log group."""
    print("::endgroup::")


@dataclass(frozen=True, slots=True)
class ChangedLineRange:
    """A changed line range in a file."""

    start: int
    end: int

    def overlaps(self, line_start: int, line_end: int) -> bool:
        """Return whether the range overlaps a source span."""
        return not (line_end < self.start or line_start > self.end)


@dataclass(frozen=True, slots=True)
class ChangedFile:
    """A changed Python file with optional changed line ranges."""

    path: Path
    ranges: tuple[ChangedLineRange, ...]


@dataclass(frozen=True, slots=True)
class ImpactEntry:
    """Impact summary for a changed symbol."""

    node: Node
    blast_radius: int
    high_risk_callers: tuple[Node, ...]
    affected_nodes: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class SeverityThresholds:
    """Thresholds for low/medium/high impact classification."""

    low_max: int = 10
    medium_max: int = 25


@dataclass(frozen=True, slots=True)
class CoverageAssessment:
    """Structural coverage signals for the current PR."""

    impacted_nodes: int
    touched_impacted_nodes: int
    impacted_files: int
    touched_impacted_files: int
    changed_test_files: int
    status: str


def run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def parse_changed_files(diff_text: str, repo_root: Path) -> list[ChangedFile]:
    """Parse unified=0 diff output into changed Python files and line ranges."""
    changed: dict[Path, list[ChangedLineRange]] = {}
    current_path: Path | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            rel = line[6:]
            current_path = None if rel == "/dev/null" else (repo_root / rel).resolve()
            continue

        if not line.startswith("@@") or current_path is None:
            continue

        header = line.split("@@")[1].strip()
        parts = header.split(" ")
        new_span = next((part for part in parts if part.startswith("+")), None)
        if new_span is None:
            continue

        start, length = _parse_hunk_span(new_span[1:])
        end = start if length == 0 else start + length - 1
        changed.setdefault(current_path, []).append(ChangedLineRange(start=start, end=end))

    files: list[ChangedFile] = []
    for path, ranges in changed.items():
        if path.suffix == ".py":
            files.append(ChangedFile(path=path, ranges=tuple(ranges)))
    return sorted(files, key=lambda item: str(item.path))


def _parse_hunk_span(span: str) -> tuple[int, int]:
    """Parse a unified diff hunk span."""
    if "," in span:
        start_str, length_str = span.split(",", maxsplit=1)
        return int(start_str), int(length_str)
    return int(span), 1


def collect_changed_files(repo_root: Path, base_ref: str, head_ref: str) -> list[ChangedFile]:
    """Collect changed Python files between two git refs."""
    diff_text = run_git(
        ["diff", "--unified=0", "--no-color", base_ref, head_ref, "--", "*.py"],
        cwd=repo_root,
    )
    return parse_changed_files(diff_text, repo_root)


def map_changed_files_to_nodes(graph_nodes: list[Node], changed_files: list[ChangedFile]) -> list[Node]:
    """Map changed files and line ranges to the most relevant graph nodes."""
    by_path: dict[Path, list[Node]] = {}
    for node in graph_nodes:
        if node.file_path is None:
            continue
        resolved = Path(node.file_path).resolve()
        by_path.setdefault(resolved, []).append(node)

    selected: dict[str, Node] = {}

    for changed_file in changed_files:
        candidates = by_path.get(changed_file.path, [])
        specific_nodes = _select_specific_overlapping_nodes(candidates, changed_file.ranges)
        if specific_nodes:
            for node in specific_nodes:
                selected[node.id] = node
            continue

        module_candidates = [node for node in candidates if node.type == NodeType.MODULE]
        if module_candidates:
            for node in module_candidates:
                selected[node.id] = node

    return sorted(selected.values(), key=lambda node: node.id)


def _select_specific_overlapping_nodes(
    candidates: list[Node],
    changed_ranges: tuple[ChangedLineRange, ...],
) -> list[Node]:
    """Select the most specific overlapping nodes for the changed ranges."""
    selected: dict[str, Node] = {}

    for changed_range in changed_ranges:
        overlapping = [
            node
            for node in candidates
            if node.location is not None
            and changed_range.overlaps(node.location.line_start, node.location.line_end)
        ]
        if not overlapping:
            continue

        best_rank = min(_node_specificity_rank(node) for node in overlapping)
        for node in overlapping:
            if _node_specificity_rank(node) == best_rank:
                selected[node.id] = node

    return sorted(selected.values(), key=lambda node: node.id)


def _node_specificity_rank(node: Node) -> tuple[int, int, int]:
    """Rank nodes by how specifically they describe a changed span."""
    if node.location is None:
        span = 10**9
    else:
        span = node.location.line_end - node.location.line_start

    type_rank = {
        NodeType.FUNCTION: 0,
        NodeType.CLASS: 1,
        NodeType.MODULE: 2,
    }.get(node.type, 3)

    depth = node.id.count(".")
    return (type_rank, span, -depth)


def build_impact_entries(
    graph_nodes: list[Node],
    query_engine: QueryEngine,
    changed_files: list[ChangedFile],
    max_depth: int,
    max_callers: int,
) -> list[ImpactEntry]:
    """Compute impact entries for changed files."""
    changed_nodes = map_changed_files_to_nodes(graph_nodes, changed_files)
    entries: list[ImpactEntry] = []

    for node in changed_nodes:
        blast = query_engine.find_blast_radius(node.id, max_depth=max_depth, direction="both")
        reverse = query_engine.get_reverse_dependencies(node.id, transitive=True)
        unique_callers = list(dict.fromkeys(caller.id for caller in reverse.dependencies))
        caller_map = {caller.id: caller for caller in reverse.dependencies}
        callers = tuple(caller_map[caller_id] for caller_id in sorted(unique_callers)[:max_callers])
        entries.append(
            ImpactEntry(
                node=node,
                blast_radius=blast.count,
                high_risk_callers=callers,
                affected_nodes=tuple(sorted(blast.affected_nodes, key=lambda item: item.id)),
            )
        )

    return sorted(entries, key=lambda item: (-item.blast_radius, item.node.id))


def classify_severity(blast_radius: int, thresholds: SeverityThresholds) -> str:
    """Classify impact severity from a blast-radius count."""
    if blast_radius <= thresholds.low_max:
        return "low"
    if blast_radius <= thresholds.medium_max:
        return "medium"
    return "high"


def _is_test_path(path: Path) -> bool:
    """Return whether a path looks like a Python test file."""
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def assess_pr_coverage(entries: list[ImpactEntry], changed_files: list[ChangedFile]) -> CoverageAssessment:
    """Estimate whether the PR appears to touch the structurally impacted area."""
    changed_paths = {changed_file.path.resolve() for changed_file in changed_files}
    changed_test_files = sum(1 for path in changed_paths if _is_test_path(path))

    impacted_nodes: dict[str, Node] = {}
    for entry in entries:
        impacted_nodes[entry.node.id] = entry.node
        for node in entry.affected_nodes:
            impacted_nodes[node.id] = node

    impacted_file_paths = {
        Path(node.file_path).resolve()
        for node in impacted_nodes.values()
        if node.file_path is not None
    }
    touched_impacted_nodes = sum(
        1
        for node in impacted_nodes.values()
        if node.file_path is not None and Path(node.file_path).resolve() in changed_paths
    )
    touched_impacted_files = len(impacted_file_paths & changed_paths)

    if not impacted_nodes:
        status = "unknown"
    elif touched_impacted_files == 0:
        status = "uncovered"
    elif touched_impacted_files == len(impacted_file_paths) and changed_test_files > 0:
        status = "well-covered"
    else:
        status = "partial"

    return CoverageAssessment(
        impacted_nodes=len(impacted_nodes),
        touched_impacted_nodes=touched_impacted_nodes,
        impacted_files=len(impacted_file_paths),
        touched_impacted_files=touched_impacted_files,
        changed_test_files=changed_test_files,
        status=status,
    )


def format_console_report(
    entries: list[ImpactEntry],
    changed_files: list[ChangedFile],
    thresholds: SeverityThresholds,
) -> str:
    """Format a human-readable console report."""
    total_blast_radius = sum(entry.blast_radius for entry in entries)
    overall_severity = classify_severity(total_blast_radius, thresholds)
    coverage = assess_pr_coverage(entries, changed_files)
    lines = [
        "ctxgraph impact report",
        "=====================",
        f"Changed Python files: {len(changed_files)}",
        f"Changed symbols: {len(entries)}",
        f"Combined blast radius: {total_blast_radius} nodes ({overall_severity})",
        f"PR coverage signal: {coverage.status}",
        (
            "Impacted area touched in PR: "
            f"{coverage.touched_impacted_nodes}/{coverage.impacted_nodes} nodes, "
            f"{coverage.touched_impacted_files}/{coverage.impacted_files} files"
        ),
        f"Changed test files: {coverage.changed_test_files}",
        "",
    ]

    if not entries:
        lines.append("No changed symbols could be mapped from the diff.")
        return "\n".join(lines)

    for entry in entries:
        severity = classify_severity(entry.blast_radius, thresholds)
        lines.append(f"- {entry.node.id} [{entry.node.type.name.lower()}]")
        lines.append(f"  blast radius: {entry.blast_radius} nodes ({severity})")
        if entry.high_risk_callers:
            lines.append("  high-risk callers:")
            for caller in entry.high_risk_callers:
                lines.append(f"    - {caller.id}")
        else:
            lines.append("  high-risk callers: none")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_markdown_report(
    entries: list[ImpactEntry],
    changed_files: list[ChangedFile],
    thresholds: SeverityThresholds,
) -> str:
    """Format a PR-comment friendly markdown report."""
    total_blast_radius = sum(entry.blast_radius for entry in entries)
    overall_severity = classify_severity(total_blast_radius, thresholds)
    coverage = assess_pr_coverage(entries, changed_files)
    lines = [
        "## `ctxgraph` impact report",
        "",
        f"- Changed Python files: **{len(changed_files)}**",
        f"- Changed symbols: **{len(entries)}**",
        f"- Combined blast radius: **{total_blast_radius} nodes**",
        f"- Overall severity: **{overall_severity}**",
        "",
    ]

    if not entries:
        lines.append("No changed symbols could be mapped from the PR diff.")
        return "\n".join(lines)

    lines.append("### Changed symbols")
    lines.append("")
    for entry in entries:
        severity = classify_severity(entry.blast_radius, thresholds)
        lines.append(
            f"- `{entry.node.id}` ({entry.node.type.name.lower()}, blast radius: {entry.blast_radius}, severity: {severity})"
        )

    lines.append("")
    lines.append("### PR coverage signals")
    lines.append("")
    lines.append(f"- Impacted nodes already touched in PR: **{coverage.touched_impacted_nodes}/{coverage.impacted_nodes}**")
    lines.append(f"- Impacted files already touched in PR: **{coverage.touched_impacted_files}/{coverage.impacted_files}**")
    lines.append(f"- Changed test files in PR: **{coverage.changed_test_files}**")
    lines.append(f"- Structural coverage assessment: **{coverage.status}**")

    notable_callers = [
        caller.id
        for entry in entries
        for caller in entry.high_risk_callers
    ]
    unique_callers = list(dict.fromkeys(notable_callers))
    if unique_callers:
        lines.append("")
        lines.append("### High-risk callers")
        lines.append("")
        for caller_id in unique_callers[:10]:
            lines.append(f"- `{caller_id}`")

    return "\n".join(lines)


def write_step_summary(markdown: str) -> None:
    """Write report markdown to the GitHub step summary if available."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    Path(summary_path).write_text(markdown + "\n", encoding="utf-8")


def write_markdown_output(markdown: str, output_path: Path | None) -> None:
    """Optionally write the markdown report to disk."""
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown + "\n", encoding="utf-8")


def maybe_post_pr_comment(markdown: str, repo: str, token: str, event_path: Path) -> None:
    """Post or update a PR comment using the GitHub API."""
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request")
    if not pull_request:
        log("No pull_request payload found; skipping PR comment.")
        return

    comments_url = pull_request["comments_url"]
    issue_comments = _api_request("GET", comments_url, token)
    marker = "<!-- ctxgraph-impact-report -->"
    body = marker + "\n" + markdown

    existing = next(
        (
            comment
            for comment in issue_comments
            if comment.get("body", "").startswith(marker)
        ),
        None,
    )

    if existing is not None:
        _api_request("PATCH", existing["url"], token, {"body": body})
        log("Updated existing ctxgraph PR comment.")
        return

    _api_request("POST", comments_url, token, {"body": body})
    log("Posted ctxgraph PR comment.")


def _api_request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    """Send a GitHub API request."""
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ctxgraph-action",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {exc.code} {detail}") from exc


def main(argv: list[str] | None = None) -> int:
    """Run the GitHub Action script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", default=".", help="Repository root to analyze.")
    parser.add_argument("--package-name", help="Top-level package name override.")
    parser.add_argument("--base-ref", required=True, help="Base git ref or SHA.")
    parser.add_argument("--head-ref", required=True, help="Head git ref or SHA.")
    parser.add_argument("--depth", type=int, default=2, help="Blast radius depth.")
    parser.add_argument(
        "--max-callers",
        type=int,
        default=5,
        help="Maximum high-risk callers to include per changed symbol.",
    )
    parser.add_argument(
        "--comment-mode",
        choices=("none", "pr"),
        default="pr",
        help="Whether to post a PR comment.",
    )
    parser.add_argument(
        "--markdown-out",
        help="Optional path to write the generated markdown report.",
    )
    parser.add_argument(
        "--low-max",
        type=int,
        default=10,
        help="Maximum blast radius counted as low severity.",
    )
    parser.add_argument(
        "--medium-max",
        type=int,
        default=25,
        help="Maximum blast radius counted as medium severity.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_path).resolve()
    if args.low_max >= args.medium_max:
        raise ValueError("--low-max must be less than --medium-max")
    thresholds = SeverityThresholds(low_max=args.low_max, medium_max=args.medium_max)

    group("ctxgraph: detect changed files")
    changed_files = collect_changed_files(repo_root, args.base_ref, args.head_ref)
    for changed_file in changed_files:
        ranges = ", ".join(f"{item.start}-{item.end}" for item in changed_file.ranges) or "n/a"
        log(f"{changed_file.path.relative_to(repo_root)} [{ranges}]")
    endgroup()

    if not changed_files:
        report = "ctxgraph impact report\n=====================\nNo changed Python files detected."
        log(report)
        write_step_summary("## `ctxgraph` impact report\n\nNo changed Python files detected.")
        return 0

    group("ctxgraph: build graph")
    graph = build_graph(repo_root, package_name=args.package_name)
    query_engine = QueryEngine(graph)
    graph_nodes = list(graph.nodes())
    log(f"Repository: {repo_root}")
    log(f"Graph nodes: {graph.node_count}")
    log(f"Graph edges: {graph.edge_count}")
    endgroup()

    group("ctxgraph: compute impact")
    entries = build_impact_entries(graph_nodes, query_engine, changed_files, args.depth, args.max_callers)
    console_report = format_console_report(entries, changed_files, thresholds)
    log(console_report)
    endgroup()

    markdown = format_markdown_report(entries, changed_files, thresholds)
    write_step_summary(markdown)
    write_markdown_output(markdown, Path(args.markdown_out) if args.markdown_out else None)

    if args.comment_mode == "pr":
        token = os.environ.get("GITHUB_TOKEN")
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if token and event_path and repo:
            maybe_post_pr_comment(markdown, repo, token, Path(event_path))
        else:
            log("PR comment skipped; missing GITHUB_TOKEN, GITHUB_EVENT_PATH, or GITHUB_REPOSITORY.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
