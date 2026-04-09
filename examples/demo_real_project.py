"""Run ctxgraph against a real, well-known Python project.

Downloads httpx (a popular HTTP client) into a temp directory and builds
a graph from its source. httpx is ideal: small enough to parse fast,
large enough to be interesting, and familiar to most Python developers.

Usage:
    python examples/demo_real_project.py
    python examples/demo_real_project.py --project requests
    python examples/demo_real_project.py --project httpx
    python examples/demo_real_project.py --local /path/to/your/project

What this shows:
  - hotspots (most depended-on symbols)
  - blast radius of a core class
  - call graph depth
  - context packing for a realistic query
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ctxgraph import QueryEngine, build_graph, pack_minimal_context, rank_context_for_query
from ctxgraph.graph.types import EdgeType

SEP = "=" * 68

PROJECTS = {
    "httpx":    ("https://github.com/encode/httpx.git",    "httpx",    "httpx"),
    "requests": ("https://github.com/psf/requests.git",    "requests", "requests"),
    "flask":    ("https://github.com/pallets/flask.git",   "flask",    "flask/src/flask"),
    "rich":     ("https://github.com/Textualize/rich.git", "rich",     "rich"),
}


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def clone_project(name: str, tmp_dir: Path) -> Path:
    url, _pkg, src_subdir = PROJECTS[name]
    dest = tmp_dir / name
    print(f"Cloning {url} ...")
    subprocess.run(
        ["git", "clone", "--depth=1", "--quiet", url, str(dest)],
        check=True,
    )
    src_path = dest / src_subdir
    if not src_path.exists():
        src_path = dest
    return src_path


def run_demo(src_path: Path, package_name: str) -> None:
    section(f"1. Build graph from {src_path.name}")
    graph = build_graph(src_path, package_name=package_name)
    stats = graph.stats()

    print(f"Path   : {src_path}")
    print(f"Nodes  : {graph.node_count}")
    print(f"Edges  : {graph.edge_count}")
    print()

    from ctxgraph.graph.types import NodeType
    for node_type, count in sorted(stats["nodes_by_type"].items(), key=lambda x: x[0].name):
        print(f"  {node_type.name.lower():<12} {count}")
    print()
    for edge_type, count in sorted(stats["edges_by_type"].items(), key=lambda x: x[0].name):
        print(f"  {edge_type.name.lower():<12} {count}")

    calls_count = stats["edges_by_type"].get(EdgeType.CALLS, 0)
    print(f"\n  CALLS edges resolved: {calls_count}")

    # ── Hotspots ──────────────────────────────────────────────────────────
    section("2. Hotspots — most depended-on symbols")

    scored = sorted(
        graph.nodes(),
        key=lambda n: len(graph.get_incoming_edges(n.id)),
        reverse=True,
    )
    print(f"{'Rank':>4}  {'In-degree':>10}  {'Type':<10}  ID")
    print("-" * 68)
    for rank, node in enumerate(scored[:15], 1):
        deg = len(graph.get_incoming_edges(node.id))
        if deg == 0:
            break
        short_id = node.id if len(node.id) <= 48 else "..." + node.id[-45:]
        print(f"{rank:>4}  {deg:>10}  {node.type.name.lower():<10}  {short_id}")

    # ── Blast radius of top hotspot ───────────────────────────────────────
    top_node = scored[0]
    section(f"3. Blast radius of top hotspot: {top_node.id}")

    engine = QueryEngine(graph)
    blast = engine.find_blast_radius(top_node.id, max_depth=2, direction="both")
    print(f"Affected at depth=2: {blast.count} nodes")
    for dist in (1, 2):
        nodes_at = sorted(blast.nodes_at_distance(dist), key=lambda n: n.id)
        if nodes_at:
            print(f"\n  {dist} hop{'s' if dist > 1 else ''}  ({len(nodes_at)} nodes):")
            for n in nodes_at[:8]:
                print(f"    {n.id}")
            if len(nodes_at) > 8:
                print(f"    ... and {len(nodes_at) - 8} more")

    # ── Call graph sample ─────────────────────────────────────────────────
    section("4. Call graph sample (CALLS edges)")

    calls = [e for e in graph.edges() if e.type == EdgeType.CALLS]
    print(f"Total CALLS edges: {len(calls)}\n")
    for edge in sorted(calls, key=lambda e: e.source_id)[:12]:
        print(f"  {edge.source_id}")
        print(f"    --> {edge.target_id}")

    # ── Context retrieval ─────────────────────────────────────────────────
    section("5. Graph-aware context packing")

    query = "HTTP request sending and response handling"
    packed = pack_minimal_context(graph, query, token_budget=3000)
    ranked = rank_context_for_query(graph, query)

    print(f"Query  : {query!r}")
    print(f"Budget : 3000 tokens")
    print(f"Packed : {len(packed.nodes)} nodes, ~{packed.estimated_tokens} tokens "
          f"({packed.utilization:.1f}%)")
    print(f"\nTop 8 ranked:")
    for s in ranked.ranked_nodes[:8]:
        print(f"  {s.score:5.2f}  {s.node.id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--project",
        choices=list(PROJECTS),
        default="httpx",
        help="Well-known project to clone and analyse (default: httpx).",
    )
    group.add_argument(
        "--local",
        metavar="PATH",
        help="Path to a local Python project to analyse instead.",
    )
    parser.add_argument(
        "--package-name",
        help="Override the top-level package name.",
    )
    args = parser.parse_args()

    if args.local:
        src_path = Path(args.local).resolve()
        package_name = args.package_name or src_path.name
        run_demo(src_path, package_name)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            _, pkg_name, _ = PROJECTS[args.project]
            src_path = clone_project(args.project, Path(tmp))
            package_name = args.package_name or pkg_name
            run_demo(src_path, package_name)


if __name__ == "__main__":
    main()
