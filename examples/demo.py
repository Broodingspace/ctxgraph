"""ctxgraph demo script.

Demonstrates the full library stack against the bundled sample_project fixture:
  - building a graph from a Python codebase
  - inspecting graph statistics
  - querying dependencies and reverse dependencies
  - blast radius analysis
  - path tracing
  - graph-aware context retrieval
  - minimal context packing for LLM use
  - JSON export and reload

Run from the repo root:
    python examples/demo.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ctxgraph import (
    QueryEngine,
    RetrievalEngine,
    build_graph,
    load_graph,
    pack_minimal_context,
    rank_context_for_query,
    save_graph,
)

SAMPLE_PROJECT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_project"

SEP = "=" * 60


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ---------------------------------------------------------------------------
# 1. Build the graph
# ---------------------------------------------------------------------------
section("1. Build graph from sample_project")

graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
stats = graph.stats()

print(f"Repository : {SAMPLE_PROJECT}")
print(f"Nodes      : {graph.node_count}")
print(f"Edges      : {graph.edge_count}")
print()
print("Node types:")
for node_type, count in sorted(stats["nodes_by_type"].items(), key=lambda x: x[0].name):
    print(f"  {node_type.name.lower():<12} {count}")
print()
print("Edge types:")
for edge_type, count in sorted(stats["edges_by_type"].items(), key=lambda x: x[0].name):
    print(f"  {edge_type.name.lower():<12} {count}")


# ---------------------------------------------------------------------------
# 2. Inspect nodes
# ---------------------------------------------------------------------------
section("2. Inspect a symbol")

node = graph.get_node("sample_project.models.User")
if node:
    print(f"ID       : {node.id}")
    print(f"Name     : {node.name}")
    print(f"Type     : {node.type.name}")
    if node.location:
        print(f"Location : {Path(node.location.file_path).name}:{node.location.line_start}")
    if node.metadata.get("docstring"):
        print(f"Docstring: {node.metadata['docstring']}")
    if node.metadata.get("base_classes"):
        print(f"Bases    : {node.metadata['base_classes']}")
else:
    print("Node not found — check that the fixture parsed correctly.")


# ---------------------------------------------------------------------------
# 3. Dependencies and reverse dependencies
# ---------------------------------------------------------------------------
section("3. Dependencies for services.UserService")

engine = QueryEngine(graph)
user_service_id = "sample_project.services.UserService"

node = graph.get_node(user_service_id)
if node:
    deps = engine.get_dependencies(user_service_id)
    print(f"Direct dependencies of {user_service_id}:")
    if deps.dependencies:
        seen: set[str] = set()
        for dep in sorted(deps.dependencies, key=lambda n: n.id):
            if dep.id in seen:
                continue
            seen.add(dep.id)
            edge_types = ", ".join(
                et.name.lower()
                for et in sorted(deps.dependency_types.get(dep.id, []), key=lambda e: e.name)
            )
            print(f"  {dep.id}  [{edge_types}]")
    else:
        print("  (none)")

    print()
    rev = engine.get_reverse_dependencies("sample_project.models.User")
    print("What depends on sample_project.models.User?")
    if rev.dependencies:
        seen_rev: set[str] = set()
        for dep in sorted(rev.dependencies, key=lambda n: n.id):
            if dep.id not in seen_rev:
                seen_rev.add(dep.id)
                print(f"  {dep.id}")
    else:
        print("  (none — IMPORTS edges may not cross files in v1)")
else:
    print(f"Node {user_service_id!r} not found.")


# ---------------------------------------------------------------------------
# 4. Blast radius
# ---------------------------------------------------------------------------
section("4. Blast radius for models.User")

target = "sample_project.models.User"
node = graph.get_node(target)
if node:
    result = engine.find_blast_radius(target, max_depth=2, direction="both")
    print(f"Origin : {result.origin.id}")
    print(f"Affected: {result.count} nodes within 2 hops (direction=both)")
    for distance in range(1, 3):
        nodes_at = sorted(result.nodes_at_distance(distance), key=lambda n: n.id)
        if nodes_at:
            print(f"  {distance} hop{'s' if distance != 1 else ''}:")
            for n in nodes_at:
                print(f"    {n.id}")
else:
    print(f"Node {target!r} not found.")


# ---------------------------------------------------------------------------
# 5. Path tracing
# ---------------------------------------------------------------------------
section("5. Trace path: api -> db")

# Find any api module and db module that are in the graph
api_candidates = [n.id for n in graph.nodes() if "api" in n.id and "." not in n.id.replace("sample_project.", "", 1)]
db_candidates = [n.id for n in graph.nodes() if n.id.endswith(".db")]

source = next(iter(api_candidates), None) or "sample_project.api"
target = next(iter(db_candidates), None) or "sample_project.db"

src_node = graph.get_node(source)
tgt_node = graph.get_node(target)

if src_node and tgt_node:
    path_result = engine.trace_path(source, target)
    if path_result.exists:
        print(f"Path from {source}")
        print(f"       to {target}:")
        print(f"  Length: {path_result.length} hop(s)")
        for idx, node_id in enumerate(path_result.path):
            print(f"  {node_id}")
            if idx < len(path_result.edges):
                print(f"    --[{path_result.edges[idx].name.lower()}]-->")
    else:
        print(f"No path found from {source} to {target}.")
        print("(IMPORTS edges in v1 only connect intra-repo modules that import each other)")
else:
    print(f"Could not find nodes: source={source}, target={target}")
    print("Listing all module node IDs in the graph:")
    for n in sorted(graph.nodes(), key=lambda x: x.id):
        if "." not in n.id.replace("sample_project.", "", 1):
            print(f"  {n.id}")


# ---------------------------------------------------------------------------
# 6. Related context neighborhood
# ---------------------------------------------------------------------------
section("6. Related context for models.User (radius=2)")

user_node = graph.get_node("sample_project.models.User")
if user_node:
    ctx = engine.get_related_context("sample_project.models.User", radius=2)
    print(f"Context size: {ctx.total_size} nodes")
    print(f"Files involved: {len(ctx.get_files())}")
    for layer_depth in sorted(ctx.layers.keys()):
        layer_nodes = sorted(ctx.layers[layer_depth], key=lambda n: n.id)
        label = "origin" if layer_depth == 0 else f"{layer_depth} hop{'s' if layer_depth != 1 else ''} away"
        print(f"  [{label}]")
        for n in layer_nodes:
            print(f"    {n.id}  ({n.type.name.lower()})")
else:
    print("Node sample_project.models.User not found.")


# ---------------------------------------------------------------------------
# 7. Graph-aware retrieval
# ---------------------------------------------------------------------------
section("7. Rank context for query: 'user authentication'")

ranked = rank_context_for_query(graph, "user authentication")
print(f"Total nodes scored: {ranked.total_scored}")
print(f"Top 5 results for query '{ranked.query}':")
for scored in ranked.ranked_nodes[:5]:
    print(f"  {scored.score:5.2f}  {scored.node.id}  ({scored.node.type.name.lower()})")
    breakdown = ", ".join(f"{k}={v:.2f}" for k, v in scored.score_breakdown.items())
    print(f"         [{breakdown}]")


# ---------------------------------------------------------------------------
# 8. Minimal context packing
# ---------------------------------------------------------------------------
section("8. Pack minimal context (budget=1500 tokens)")

context = pack_minimal_context(graph, "database connection", token_budget=1500)
print(f"Query     : {context.query!r}")
print(f"Budget    : {context.token_budget} tokens")
print(f"Used      : ~{context.estimated_tokens} tokens ({context.utilization:.1f}%)")
print(f"Nodes     : {len(context.nodes)}")
for n in sorted(context.nodes, key=lambda x: x.id):
    print(f"  {n.id}  ({n.type.name.lower()})")


# ---------------------------------------------------------------------------
# 9. Export and reload
# ---------------------------------------------------------------------------
section("9. Export graph to JSON and reload")

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    export_path = Path(f.name)

save_graph(graph, export_path)
print(f"Saved to: {export_path}")
print(f"File size: {export_path.stat().st_size:,} bytes")

reloaded = load_graph(export_path)
print(f"Reloaded: {reloaded.node_count} nodes, {reloaded.edge_count} edges")
assert reloaded.node_count == graph.node_count
assert reloaded.edge_count == graph.edge_count
print("Round-trip assertion passed.")

export_path.unlink()


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
section("Done")
print("All demo sections completed.")
print()
print("Explore further:")
print("  ctxgraph build ./tests/fixtures/sample_project")
print("  ctxgraph blast-radius --repo ./tests/fixtures/sample_project \\")
print("      sample_project.models.User --depth 2 --direction both")
print("  ctxgraph export ./tests/fixtures/sample_project --out graph.json")
print("  ctxgraph inspect --graph-file graph.json sample_project.services.UserService")
