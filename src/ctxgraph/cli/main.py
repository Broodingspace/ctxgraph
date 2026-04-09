"""Command-line interface for ctxgraph."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from ..exporters import export_graph_json, graph_to_dict
from ..graph import CodeGraph, NodeType
from ..io import load_graph
from ..parser import build_graph
from ..query import QueryEngine
from ..retrieval import pack_minimal_context, rank_context_for_query


class CLIError(Exception):
    """Raised when CLI execution fails with a user-facing error."""


class ArgumentParser(argparse.ArgumentParser):
    """Argument parser with consistent CLI error formatting."""

    def error(self, message: str) -> NoReturn:
        raise CLIError(message)


def build_parser() -> ArgumentParser:
    """Build the root argument parser."""
    parser = ArgumentParser(
        prog="ctxgraph",
        description=(
            "Build and query graph-aware code context from Python repositories."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_cmd = subparsers.add_parser(
        "build",
        help="Build a graph from a repository and print a summary.",
        description="Parse a repository and print graph summary statistics.",
    )
    _add_repo_build_args(build_cmd)
    build_cmd.set_defaults(handler=_handle_build)

    load_cmd = subparsers.add_parser(
        "load",
        help="Load a serialized graph and print a summary.",
        description="Load a previously exported graph and print summary statistics.",
    )
    _add_graph_file_arg(load_cmd)
    load_cmd.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text output.",
    )
    load_cmd.set_defaults(handler=_handle_load)

    inspect_cmd = subparsers.add_parser(
        "inspect",
        help="Inspect a symbol by ID.",
        description="Build a graph from a repository and inspect a specific symbol.",
    )
    _add_graph_input_args(inspect_cmd)
    inspect_cmd.add_argument("symbol_id", help="Fully qualified symbol ID to inspect.")
    inspect_cmd.set_defaults(handler=_handle_inspect)

    deps_cmd = subparsers.add_parser(
        "deps",
        help="Show dependencies or reverse dependencies for a symbol.",
        description="Build a graph and print dependency relationships for a symbol.",
    )
    _add_graph_input_args(deps_cmd)
    deps_cmd.add_argument("symbol_id", help="Fully qualified symbol ID to inspect.")
    deps_cmd.add_argument(
        "--reverse",
        action="store_true",
        help="Show reverse dependencies instead of outgoing dependencies.",
    )
    deps_cmd.add_argument(
        "--transitive",
        action="store_true",
        help="Traverse dependencies transitively.",
    )
    deps_cmd.set_defaults(handler=_handle_deps)

    blast_cmd = subparsers.add_parser(
        "blast-radius",
        help="Show nodes within N hops of a symbol.",
        description="Build a graph and print blast-radius analysis for a symbol.",
    )
    _add_graph_input_args(blast_cmd)
    blast_cmd.add_argument("symbol_id", help="Fully qualified symbol ID to inspect.")
    blast_cmd.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Maximum traversal depth.",
    )
    blast_cmd.add_argument(
        "--direction",
        choices=("outgoing", "incoming", "both"),
        default="outgoing",
        help="Traversal direction to use for blast-radius analysis.",
    )
    blast_cmd.set_defaults(handler=_handle_blast_radius)

    trace_cmd = subparsers.add_parser(
        "trace",
        help="Trace the shortest graph path between two symbols.",
        description="Build a graph and trace the shortest path between two symbols.",
    )
    _add_graph_input_args(trace_cmd)
    trace_cmd.add_argument("source_id", help="Source symbol ID.")
    trace_cmd.add_argument("target_id", help="Target symbol ID.")
    trace_cmd.set_defaults(handler=_handle_trace)

    export_cmd = subparsers.add_parser(
        "export",
        help="Export a graph to disk.",
        description="Parse a repository and export its graph as JSON.",
    )
    _add_repo_build_args(export_cmd)
    export_cmd.add_argument(
        "--format",
        choices=("json",),
        default="json",
        help="Export format.",
    )
    export_cmd.add_argument(
        "--out",
        required=True,
        help="Output file path.",
    )
    export_cmd.set_defaults(handler=_handle_export)

    hotspots_cmd = subparsers.add_parser(
        "hotspots",
        help="List the most-connected symbols in the graph.",
        description=(
            "Build a graph and rank symbols by incoming edge count. "
            "Surfaces the nodes most depended on — useful for onboarding, "
            "risk assessment, and finding critical paths."
        ),
    )
    _add_graph_input_args(hotspots_cmd)
    hotspots_cmd.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top symbols to show (default: 10).",
    )
    hotspots_cmd.add_argument(
        "--type",
        dest="node_type_filter",
        choices=("any", "function", "class", "module"),
        default="any",
        help="Only show nodes of this type (default: any).",
    )
    hotspots_cmd.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    hotspots_cmd.set_defaults(handler=_handle_hotspots)

    context_cmd = subparsers.add_parser(
        "context",
        help="Rank and pack context for a query (graph-aware, no embeddings).",
        description=(
            "Build a graph and retrieve the most relevant symbols for a text query "
            "using structural scoring. Packs results within a token budget."
        ),
    )
    _add_graph_input_args(context_cmd)
    context_cmd.add_argument("query", help="Natural language query (e.g. 'user authentication').")
    context_cmd.add_argument(
        "--budget",
        type=int,
        default=3000,
        help="Token budget for context packing (default: 3000).",
    )
    context_cmd.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum ranked results to show before packing (default: 10).",
    )
    context_cmd.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    context_cmd.set_defaults(handler=_handle_context)

    return parser


def _add_repo_build_args(parser: argparse.ArgumentParser) -> None:
    """Add repository build arguments to a parser."""
    parser.add_argument("repo_path", help="Path to the Python repository to parse.")
    parser.add_argument(
        "--package-name",
        help="Top-level package name. Defaults to the repository directory name.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude. Can be passed multiple times.",
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Exclude test files from graph construction.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text output.",
    )


def _add_repo_query_args(parser: argparse.ArgumentParser) -> None:
    """Add repository query arguments to a parser."""
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the Python repository to parse. Defaults to the current directory.",
    )
    parser.add_argument(
        "--package-name",
        help="Top-level package name. Defaults to the repository directory name.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude. Can be passed multiple times.",
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Exclude test files from graph construction.",
    )


def _add_graph_file_arg(parser: argparse.ArgumentParser) -> None:
    """Add a serialized graph file argument to a parser."""
    parser.add_argument(
        "graph_file",
        help="Path to a serialized ctxgraph JSON file.",
    )


def _add_graph_input_args(parser: argparse.ArgumentParser) -> None:
    """Add repository or graph-file input arguments to a parser."""
    parser.add_argument(
        "--repo",
        help="Path to the Python repository to parse.",
    )
    parser.add_argument(
        "--graph-file",
        help="Path to a serialized ctxgraph JSON file to query instead of rebuilding.",
    )
    parser.add_argument(
        "--package-name",
        help="Top-level package name. Defaults to the repository directory name.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude. Can be passed multiple times.",
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Exclude test files from graph construction.",
    )


def _build_graph_from_args(args: argparse.Namespace, repo_attr: str) -> tuple[CodeGraph, Path]:
    """Build a graph from parsed CLI arguments."""
    repo_path = Path(getattr(args, repo_attr)).resolve()
    if not repo_path.exists():
        raise CLIError(f"Repository path does not exist: {repo_path}")
    if not repo_path.is_dir():
        raise CLIError(f"Repository path is not a directory: {repo_path}")

    graph = build_graph(
        repo_path,
        package_name=args.package_name,
        exclude_dirs=set(args.exclude_dir) if args.exclude_dir else None,
        include_tests=not args.no_tests,
    )
    return graph, repo_path


def _load_graph_from_path(graph_path: str) -> tuple[CodeGraph, Path]:
    """Load a serialized graph from disk."""
    path = Path(graph_path).resolve()
    if not path.exists():
        raise CLIError(f"Graph file does not exist: {path}")
    if not path.is_file():
        raise CLIError(f"Graph file is not a file: {path}")
    return load_graph(path), path


def _resolve_graph_input(args: argparse.Namespace) -> tuple[CodeGraph, str]:
    """Resolve CLI graph input from either a repo path or graph file."""
    if args.graph_file:
        graph, path = _load_graph_from_path(args.graph_file)
        return graph, str(path)

    repo = args.repo or "."
    graph, repo_path = _build_graph_from_args(
        argparse.Namespace(
            repo=repo,
            package_name=args.package_name,
            exclude_dir=args.exclude_dir,
            no_tests=args.no_tests,
        ),
        "repo",
    )
    return graph, str(repo_path)


def _handle_build(args: argparse.Namespace) -> int:
    """Handle the build command."""
    graph, repo_path = _build_graph_from_args(args, "repo_path")
    if args.json:
        print(json.dumps(graph_to_dict(graph, source_path=str(repo_path))["summary"], indent=2))
        return 0

    print(f"Repository: {repo_path}")
    print(f"Nodes: {graph.node_count}")
    print(f"Edges: {graph.edge_count}")

    stats = graph.stats()
    print("Node types:")
    for node_type, count in sorted(stats["nodes_by_type"].items(), key=lambda item: item[0].name):
        print(f"  {node_type.name.lower()}: {count}")
    print("Edge types:")
    for edge_type, count in sorted(stats["edges_by_type"].items(), key=lambda item: item[0].name):
        print(f"  {edge_type.name.lower()}: {count}")
    return 0


def _handle_load(args: argparse.Namespace) -> int:
    """Handle the load command."""
    graph, graph_path = _load_graph_from_path(args.graph_file)
    payload = graph_to_dict(graph, source_path=graph_path)["summary"]
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Graph file: {graph_path}")
    print(f"Nodes: {payload['total_nodes']}")
    print(f"Edges: {payload['total_edges']}")
    print("Node types:")
    for node_type, count in sorted(payload["nodes_by_type"].items()):
        print(f"  {node_type}: {count}")
    print("Edge types:")
    for edge_type, count in sorted(payload["edges_by_type"].items()):
        print(f"  {edge_type}: {count}")
    return 0


def _handle_inspect(args: argparse.Namespace) -> int:
    """Handle the inspect command."""
    graph, input_source = _resolve_graph_input(args)
    node = graph.get_node(args.symbol_id)
    if node is None:
        raise CLIError(f"Symbol not found: {args.symbol_id}")

    engine = QueryEngine(graph)
    deps = engine.get_dependencies(node.id)
    reverse_deps = engine.get_reverse_dependencies(node.id)

    print(f"Source: {input_source}")
    print(f"ID: {node.id}")
    print(f"Name: {node.name}")
    print(f"Type: {node.type.name.lower()}")
    if node.location is not None:
        print(
            f"Location: {node.location.file_path}:{node.location.line_start}-{node.location.line_end}"
        )
    if node.metadata:
        print("Metadata:")
        for key, value in sorted(node.metadata.items()):
            print(f"  {key}: {value}")
    print(f"Dependencies: {deps.count}")
    print(f"Reverse dependencies: {reverse_deps.count}")
    return 0


def _handle_deps(args: argparse.Namespace) -> int:
    """Handle the deps command."""
    graph, _input_source = _resolve_graph_input(args)
    engine = QueryEngine(graph)

    if args.reverse:
        result = engine.get_reverse_dependencies(args.symbol_id, transitive=args.transitive)
        heading = "Reverse dependencies"
    else:
        result = engine.get_dependencies(args.symbol_id, transitive=args.transitive)
        heading = "Dependencies"

    qualifier = "transitive" if args.transitive else "direct"
    print(f"{heading} for {result.node.id} ({qualifier}):")
    if not result.dependencies:
        print("  none")
        return 0

    for dependency in sorted(result.dependencies, key=lambda node: node.id):
        edge_types = ",".join(
            edge_type.name.lower()
            for edge_type in sorted(
                result.dependency_types.get(dependency.id, []),
                key=lambda item: item.name,
            )
        )
        suffix = f" [{edge_types}]" if edge_types else ""
        print(f"  {dependency.id}{suffix}")
    return 0


def _handle_blast_radius(args: argparse.Namespace) -> int:
    """Handle the blast-radius command."""
    if args.depth < 1:
        raise CLIError("--depth must be >= 1")

    graph, _input_source = _resolve_graph_input(args)
    engine = QueryEngine(graph)
    result = engine.find_blast_radius(
        args.symbol_id,
        max_depth=args.depth,
        direction=args.direction,
    )

    print(
        f"Blast radius for {result.origin.id} "
        f"(depth={args.depth}, direction={args.direction}):"
    )
    if not result.affected_nodes:
        print("  none")
        return 0

    for distance in range(1, args.depth + 1):
        nodes = sorted(result.nodes_at_distance(distance), key=lambda node: node.id)
        if not nodes:
            continue
        print(f"  {distance} hop{'s' if distance != 1 else ''}:")
        for node in nodes:
            print(f"    {node.id}")
    return 0


def _handle_trace(args: argparse.Namespace) -> int:
    """Handle the trace command."""
    graph, _input_source = _resolve_graph_input(args)
    engine = QueryEngine(graph)
    result = engine.trace_path(args.source_id, args.target_id)

    if not result.exists:
        print(f"No path found from {args.source_id} to {args.target_id}.")
        return 0

    print(f"Path from {args.source_id} to {args.target_id}:")
    print(f"  Length: {result.length}")
    for index, node_id in enumerate(result.path):
        print(f"  {node_id}")
        if index < len(result.edges):
            print(f"    -> {result.edges[index].name.lower()}")
    return 0


def _handle_export(args: argparse.Namespace) -> int:
    """Handle the export command."""
    graph, repo_path = _build_graph_from_args(args, "repo_path")
    if args.format != "json":
        raise CLIError(f"Unsupported export format: {args.format}")

    destination = export_graph_json(graph, args.out, source_path=str(repo_path))
    if args.json:
        print(json.dumps({"format": args.format, "out": str(destination)}, indent=2))
    else:
        print(f"Exported {args.format} graph to {destination}")
    return 0


def _handle_hotspots(args: argparse.Namespace) -> int:
    """Handle the hotspots command."""
    if args.top < 1:
        raise CLIError("--top must be >= 1")

    graph, _input_source = _resolve_graph_input(args)

    # Filter by node type if requested
    type_map = {
        "function": NodeType.FUNCTION,
        "class": NodeType.CLASS,
        "module": NodeType.MODULE,
    }
    node_type = type_map.get(args.node_type_filter)

    # Score every node by incoming edge count (how many things depend on it)
    scored: list[tuple[int, str]] = []
    for node in graph.nodes(node_type=node_type):
        in_degree = len(graph.get_incoming_edges(node.id))
        if in_degree > 0:
            scored.append((in_degree, node.id))

    scored.sort(reverse=True)
    top = scored[: args.top]

    if args.json:
        payload = [
            {
                "id": node_id,
                "in_degree": deg,
                "type": graph.get_node(node_id).type.name.lower(),  # type: ignore[union-attr]
            }
            for deg, node_id in top
        ]
        print(json.dumps(payload, indent=2))
        return 0

    filter_label = f" ({args.node_type_filter})" if args.node_type_filter != "any" else ""
    print(f"Top {args.top} hotspots{filter_label} by incoming edges:\n")
    for rank, (deg, node_id) in enumerate(top, 1):
        node = graph.get_node(node_id)
        node_type_label = node.type.name.lower() if node else "?"
        print(f"  {rank:>3}.  {deg:>4} deps   {node_id}  ({node_type_label})")
    return 0


def _handle_context(args: argparse.Namespace) -> int:
    """Handle the context command."""
    if args.budget < 1:
        raise CLIError("--budget must be >= 1")

    graph, _input_source = _resolve_graph_input(args)

    ranked = rank_context_for_query(graph, args.query)
    packed = pack_minimal_context(graph, args.query, token_budget=args.budget)

    if args.json:
        print(json.dumps({
            "query": args.query,
            "token_budget": args.budget,
            "estimated_tokens": packed.estimated_tokens,
            "utilization": round(packed.utilization, 1),
            "ranked": [
                {
                    "id": s.node.id,
                    "score": round(s.score, 3),
                    "type": s.node.type.name.lower(),
                }
                for s in ranked.ranked_nodes[: args.top]
            ],
            "packed": [n.id for n in packed.nodes],
        }, indent=2))
        return 0

    print(f"Query: {args.query!r}\n")
    print(f"Top {args.top} ranked results:")
    for scored in ranked.ranked_nodes[: args.top]:
        print(f"  {scored.score:5.2f}  {scored.node.id}  ({scored.node.type.name.lower()})")

    print(f"\nPacked context  (budget={args.budget} tokens):")
    print(f"  Nodes  : {len(packed.nodes)}")
    print(f"  Tokens : ~{packed.estimated_tokens}  ({packed.utilization:.1f}% of budget)")
    for node in sorted(packed.nodes, key=lambda n: n.id):
        print(f"    {node.id}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ctxgraph CLI."""
    parser = build_parser()

    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        return args.handler(args)
    except CLIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
