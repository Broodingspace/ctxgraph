"""Example: Parse a Python codebase and build a code graph.

This example demonstrates how to use ctxgraph to automatically parse
a Python codebase and build a queryable graph of its structure.
"""

from pathlib import Path

from ctxgraph import EdgeType, NodeType, build_graph


def example_parse_ctxgraph_itself() -> None:
    """Example: Parse the ctxgraph package itself."""
    print("=" * 70)
    print("Example: Parsing ctxgraph Package")
    print("=" * 70)

    # Get path to ctxgraph source
    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"

    # Build the graph
    print(f"\nParsing codebase at: {src_path}")
    graph = build_graph(src_path, package_name="ctxgraph")

    # Print statistics
    print("\n" + "=" * 70)
    print("Graph Statistics")
    print("=" * 70)

    stats = graph.stats()
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")

    print("\nNodes by type:")
    for node_type, count in stats["nodes_by_type"].items():
        print(f"  {node_type.name}: {count}")

    print("\nEdges by type:")
    for edge_type, count in stats["edges_by_type"].items():
        print(f"  {edge_type.name}: {count}")

    # Find all modules
    print("\n" + "=" * 70)
    print("Modules Discovered")
    print("=" * 70)

    modules = list(graph.nodes(node_type=NodeType.MODULE))
    for module in sorted(modules, key=lambda m: m.id):
        print(f"  {module.id}")
        if module.metadata.get("docstring"):
            # Print first line of docstring
            first_line = module.metadata["docstring"].split("\n")[0]
            print(f"    -> {first_line}")

    # Find all classes
    print("\n" + "=" * 70)
    print("Classes Discovered")
    print("=" * 70)

    classes = list(graph.nodes(node_type=NodeType.CLASS))
    for cls in sorted(classes, key=lambda c: c.id)[:10]:  # Show first 10
        print(f"\n  {cls.name} ({cls.id})")
        if cls.location:
            print(f"    Location: {cls.location.file_path}:{cls.location.line_start}")

        # Show inheritance
        parents = graph.get_neighbors(cls.id, edge_type=EdgeType.INHERITS)
        if parents:
            parent_names = [p.name for p in parents]
            print(f"    Inherits from: {', '.join(parent_names)}")

        # Show methods
        methods = graph.get_neighbors(cls.id, edge_type=EdgeType.CONTAINS)
        method_funcs = [m for m in methods if m.type == NodeType.FUNCTION]
        if method_funcs:
            method_names = [m.name for m in method_funcs[:5]]
            print(f"    Methods: {', '.join(method_names)}")
            if len(method_funcs) > 5:
                print(f"    ... and {len(method_funcs) - 5} more")

    # Analyze module dependencies
    print("\n" + "=" * 70)
    print("Module Dependencies (Internal)")
    print("=" * 70)

    for module in sorted(modules, key=lambda m: m.id)[:5]:  # Show first 5
        imports = graph.get_neighbors(module.id, edge_type=EdgeType.IMPORTS)
        if imports:
            print(f"\n  {module.id} imports:")
            for imp in imports:
                print(f"    -> {imp.id}")

    # Find most connected classes
    print("\n" + "=" * 70)
    print("Most Connected Classes (by method count)")
    print("=" * 70)

    class_method_counts = []
    for cls in classes:
        methods = graph.get_neighbors(cls.id, edge_type=EdgeType.CONTAINS)
        method_funcs = [m for m in methods if m.type == NodeType.FUNCTION]
        class_method_counts.append((cls, len(method_funcs)))

    class_method_counts.sort(key=lambda x: x[1], reverse=True)

    for cls, method_count in class_method_counts[:5]:
        print(f"  {cls.name}: {method_count} methods")

    # Find async functions
    print("\n" + "=" * 70)
    print("Async Functions")
    print("=" * 70)

    functions = list(graph.nodes(node_type=NodeType.FUNCTION))
    async_funcs = [f for f in functions if f.metadata.get("is_async", False)]

    if async_funcs:
        for func in async_funcs[:10]:
            print(f"  {func.id}")
    else:
        print("  No async functions found")

    print("\n")


def example_query_patterns() -> None:
    """Example: Common query patterns on a code graph."""
    print("=" * 70)
    print("Example: Common Query Patterns")
    print("=" * 70)

    # Parse ctxgraph
    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    # Pattern 1: Find all classes that inherit from a base
    print("\nPattern 1: Find classes by inheritance")
    print("-" * 70)

    # Find all classes
    classes = list(graph.nodes(node_type=NodeType.CLASS))

    # Group by parent class
    inheritance_map: dict[str, list[str]] = {}
    for cls in classes:
        parents = graph.get_neighbors(cls.id, edge_type=EdgeType.INHERITS)
        for parent in parents:
            if parent.name not in inheritance_map:
                inheritance_map[parent.name] = []
            inheritance_map[parent.name].append(cls.name)

    for parent_name, children in sorted(inheritance_map.items()):
        print(f"  {parent_name}:")
        for child in children:
            print(f"    -> {child}")

    # Pattern 2: Find what a module defines
    print("\nPattern 2: What does a module define?")
    print("-" * 70)

    graph_module = graph.get_node("ctxgraph.graph.graph")
    if graph_module:
        defined = graph.get_neighbors(graph_module.id, edge_type=EdgeType.DEFINES)
        print(f"  {graph_module.id} defines:")
        for entity in sorted(defined, key=lambda e: e.name):
            print(f"    {entity.type.name}: {entity.name}")

    # Pattern 3: Find all methods with a specific name
    print("\nPattern 3: Find methods by name pattern")
    print("-" * 70)

    functions = list(graph.nodes(node_type=NodeType.FUNCTION))
    init_methods = [f for f in functions if f.name == "__init__"]

    print(f"  Found {len(init_methods)} __init__ methods:")
    for method in init_methods[:5]:
        print(f"    {method.id}")
    if len(init_methods) > 5:
        print(f"    ... and {len(init_methods) - 5} more")

    # Pattern 4: Calculate class complexity (method count)
    print("\nPattern 4: Calculate class complexity")
    print("-" * 70)

    classes_with_complexity = []
    for cls in classes:
        methods = graph.get_neighbors(cls.id, edge_type=EdgeType.CONTAINS)
        method_count = len([m for m in methods if m.type == NodeType.FUNCTION])
        classes_with_complexity.append((cls.name, method_count))

    classes_with_complexity.sort(key=lambda x: x[1], reverse=True)

    for class_name, method_count in classes_with_complexity[:5]:
        complexity = "High" if method_count > 10 else "Medium" if method_count > 5 else "Low"
        print(f"  {class_name}: {method_count} methods ({complexity})")

    print("\n")


def example_export_graph_data() -> None:
    """Example: Export graph data for analysis."""
    print("=" * 70)
    print("Example: Export Graph Data")
    print("=" * 70)

    # Parse ctxgraph
    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    # Export as simple dict structure (custom format)
    print("\nExporting graph structure...")

    export_data = {
        "nodes": [],
        "edges": [],
    }

    for node in graph.nodes():
        export_data["nodes"].append(
            {
                "id": node.id,
                "type": node.type.name,
                "name": node.name,
                "file": node.file_path,
                "line": node.location.line_start if node.location else None,
            }
        )

    for edge in graph.edges():
        export_data["edges"].append(
            {
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.type.name,
            }
        )

    print(f"Exported {len(export_data['nodes'])} nodes")
    print(f"Exported {len(export_data['edges'])} edges")

    # Could save to JSON here
    # import json
    # with open('graph.json', 'w') as f:
    #     json.dump(export_data, f, indent=2)

    print("\n")


if __name__ == "__main__":
    example_parse_ctxgraph_itself()
    example_query_patterns()
    example_export_graph_data()

    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
