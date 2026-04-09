"""Example: Using the Query Engine for Code Analysis.

This example demonstrates how to use ctxgraph's query engine to analyze
codebases, find dependencies, assess impact, and extract context for AI tools.
"""

from pathlib import Path

from ctxgraph import EdgeType, NodeType, QueryEngine, build_graph


def example_dependency_analysis() -> None:
    """Example: Analyze dependencies in a codebase."""
    print("=" * 70)
    print("Example 1: Dependency Analysis")
    print("=" * 70)

    # Build graph of ctxgraph itself
    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")
    engine = QueryEngine(graph)

    # Find a module to analyze
    graph_module = graph.get_node("ctxgraph.graph.graph")
    if not graph_module:
        print("Module not found")
        return

    print(f"\nAnalyzing: {graph_module.id}")
    print("-" * 70)

    # Get direct dependencies
    deps = engine.get_dependencies(graph_module.id)
    print(f"\nDirect dependencies: {deps.count}")
    for dep in deps.dependencies[:5]:
        edge_types = deps.dependency_types[dep.id]
        types_str = ", ".join(et.name for et in edge_types)
        print(f"  -> {dep.id} ({types_str})")

    # Get transitive dependencies
    transitive_deps = engine.get_dependencies(graph_module.id, transitive=True)
    print(f"\nTransitive dependencies: {transitive_deps.count}")
    print(f"  (All modules/entities this depends on)")

    # Get what depends on this module (reverse dependencies)
    reverse_deps = engine.get_reverse_dependencies(graph_module.id)
    print(f"\nReverse dependencies: {reverse_deps.count}")
    print("  (What depends on this module)")
    for dep in reverse_deps.dependencies[:5]:
        print(f"  <- {dep.id}")

    print()


def example_blast_radius_analysis() -> None:
    """Example: Find the blast radius of changes."""
    print("=" * 70)
    print("Example 2: Blast Radius Analysis")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")
    engine = QueryEngine(graph)

    # Find the CodeGraph class
    code_graph_class = graph.get_node("ctxgraph.graph.graph.CodeGraph")
    if not code_graph_class:
        print("Class not found")
        return

    print(f"\nAnalyzing blast radius for: {code_graph_class.id}")
    print("-" * 70)

    # Find immediate blast radius (depth 1)
    blast1 = engine.find_blast_radius(code_graph_class.id, max_depth=1)
    print(f"\nDepth 1 (immediate impact): {blast1.count} nodes")
    for node in blast1.nodes_at_distance(1)[:5]:
        print(f"  {node.type.name}: {node.id}")

    # Find extended blast radius (depth 2)
    blast2 = engine.find_blast_radius(code_graph_class.id, max_depth=2)
    print(f"\nDepth 2 (extended impact): {blast2.count} nodes")

    # Show breakdown by distance
    for distance in range(1, 3):
        nodes = blast2.nodes_at_distance(distance)
        if nodes:
            print(f"\n  Distance {distance}: {len(nodes)} nodes")
            by_type = {}
            for node in nodes:
                if node.type not in by_type:
                    by_type[node.type] = 0
                by_type[node.type] += 1
            for node_type, count in by_type.items():
                print(f"    {node_type.name}: {count}")

    # Find reverse blast radius (what could affect this?)
    reverse_blast = engine.find_blast_radius(
        code_graph_class.id,
        max_depth=2,
        direction="incoming"
    )
    print(f"\nReverse blast radius: {reverse_blast.count} nodes")
    print("  (What could cause this to break)")

    print()


def example_path_finding() -> None:
    """Example: Find paths between code entities."""
    print("=" * 70)
    print("Example 3: Path Finding")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")
    engine = QueryEngine(graph)

    # Find path between two modules
    source = "ctxgraph.parser.builder"
    target = "ctxgraph.graph.graph"

    print(f"\nFinding path from:")
    print(f"  Source: {source}")
    print(f"  Target: {target}")
    print("-" * 70)

    path_result = engine.trace_path(source, target)

    if path_result.exists:
        print(f"\nPath found! Length: {path_result.length} edges")
        print("\nPath:")
        for i, node_id in enumerate(path_result.path):
            if i < len(path_result.edges):
                edge_type = path_result.edges[i]
                print(f"  {node_id}")
                print(f"    |")
                print(f"    | {edge_type.name}")
                print(f"    v")
            else:
                print(f"  {node_id}")
    else:
        print("\nNo path found (entities are not connected)")

    # Try another path
    print("\n" + "=" * 70)
    parser_module = graph.get_node("ctxgraph.parser")
    if parser_module:
        # Find any function in the graph
        for node in graph.nodes(node_type=NodeType.FUNCTION):
            path = engine.trace_path(parser_module.id, node.id)
            if path.exists and path.length > 0:
                print(f"\nExample path from parser module to a function:")
                print(f"  {' -> '.join(path.path[:4])}")
                if len(path.path) > 4:
                    print(f"  ... ({len(path.path) - 4} more)")
                break

    print()


def example_context_extraction() -> None:
    """Example: Extract context for AI systems."""
    print("=" * 70)
    print("Example 4: Context Extraction for AI/LLMs")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")
    engine = QueryEngine(graph)

    # Find a function to get context for
    function_node = None
    for node in graph.nodes(node_type=NodeType.FUNCTION):
        if "add_node" in node.name:
            function_node = node
            break

    if not function_node:
        print("Function not found")
        return

    print(f"\nExtracting context for: {function_node.id}")
    print(f"  (Useful for building LLM prompts)")
    print("-" * 70)

    # Get context with radius 1
    context1 = engine.get_related_context(function_node.id, radius=1)
    print(f"\nRadius 1 context: {context1.total_size} nodes")
    print(f"  Files involved: {len(context1.get_files())}")
    print("\n  Layers:")
    for distance, nodes in sorted(context1.layers.items()):
        print(f"    Distance {distance}: {len(nodes)} nodes")

    # Get context with radius 2
    context2 = engine.get_related_context(function_node.id, radius=2)
    print(f"\nRadius 2 context: {context2.total_size} nodes")
    print(f"  Files involved: {len(context2.get_files())}")

    # Get context with type filter (only classes and functions)
    filtered_context = engine.get_related_context(
        function_node.id,
        radius=2,
        node_filter=lambda n: n.type in (NodeType.CLASS, NodeType.FUNCTION)
    )
    print(f"\nFiltered context (classes + functions): {filtered_context.total_size} nodes")

    # Show what you'd send to an LLM
    print("\n" + "-" * 70)
    print("Context for LLM prompt:")
    print("-" * 70)
    print(f"\nTarget: {function_node.id}")
    print(f"Location: {function_node.file_path}:{function_node.location.line_start if function_node.location else '?'}")
    print(f"\nRelated entities (radius 2):")
    for node in context2.context_nodes[:10]:
        if node.id != function_node.id:
            print(f"  - {node.type.name}: {node.id}")
    if context2.total_size > 10:
        print(f"  ... and {context2.total_size - 10} more")

    print()


def example_impact_analysis() -> None:
    """Example: Assess the impact of changes."""
    print("=" * 70)
    print("Example 5: Change Impact Assessment")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")
    engine = QueryEngine(graph)

    # Simulate: "I want to change the Node class"
    node_class = graph.get_node("ctxgraph.graph.node.Node")
    if not node_class:
        print("Class not found")
        return

    print(f"\nScenario: Changing {node_class.id}")
    print("  Question: What could break?")
    print("-" * 70)

    # Step 1: Find what directly uses this class
    direct_deps = engine.get_reverse_dependencies(node_class.id)
    print(f"\nStep 1: Direct dependents: {direct_deps.count}")
    print("  (These directly reference Node)")
    for dep in direct_deps.dependencies[:5]:
        print(f"  - {dep.id}")

    # Step 2: Find transitive dependents
    transitive_deps = engine.get_reverse_dependencies(node_class.id, transitive=True)
    print(f"\nStep 2: Transitive dependents: {transitive_deps.count}")
    print("  (Everything that could be affected)")

    # Step 3: Calculate blast radius
    blast = engine.find_blast_radius(node_class.id, max_depth=3, direction="incoming")
    print(f"\nStep 3: Blast radius (depth 3): {blast.count} nodes")

    # Breakdown by node type
    by_type = {}
    for node in blast.affected_nodes:
        if node.type not in by_type:
            by_type[node.type] = []
        by_type[node.type].append(node)

    print("\n  Affected by type:")
    for node_type in sorted(by_type.keys(), key=lambda t: t.name):
        count = len(by_type[node_type])
        print(f"    {node_type.name}: {count}")

    # Recommendation
    print("\n" + "-" * 70)
    print("Impact Assessment:")
    print(f"  Risk level: {'HIGH' if blast.count > 20 else 'MEDIUM' if blast.count > 10 else 'LOW'}")
    print(f"  Affected nodes: {blast.count}")
    print(f"  Recommendation: {'Careful refactoring needed' if blast.count > 20 else 'Moderate caution' if blast.count > 10 else 'Low risk change'}")

    print()


def example_dependency_chain() -> None:
    """Example: Trace dependency chains."""
    print("=" * 70)
    print("Example 6: Tracing Dependency Chains")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")
    engine = QueryEngine(graph)

    # Find modules with many dependencies
    print("\nModules with most dependencies:")
    print("-" * 70)

    dep_counts = []
    for module in graph.nodes(node_type=NodeType.MODULE):
        deps = engine.get_dependencies(module.id, edge_types=[EdgeType.IMPORTS])
        if deps.count > 0:
            dep_counts.append((module, deps.count))

    dep_counts.sort(key=lambda x: x[1], reverse=True)

    for module, count in dep_counts[:5]:
        print(f"\n  {module.id}: {count} dependencies")

        # Show the dependency chain
        deps = engine.get_dependencies(module.id, edge_types=[EdgeType.IMPORTS])
        for dep in deps.dependencies[:3]:
            print(f"    -> {dep.id}")
        if deps.count > 3:
            print(f"    ... and {deps.count - 3} more")

    # Find modules with most dependents (most important/central)
    print("\n" + "=" * 70)
    print("Most depended-upon modules:")
    print("-" * 70)

    dependent_counts = []
    for module in graph.nodes(node_type=NodeType.MODULE):
        dependents = engine.get_reverse_dependencies(
            module.id,
            edge_types=[EdgeType.IMPORTS]
        )
        if dependents.count > 0:
            dependent_counts.append((module, dependents.count))

    dependent_counts.sort(key=lambda x: x[1], reverse=True)

    for module, count in dependent_counts[:5]:
        print(f"\n  {module.id}: {count} dependents")
        print(f"    (Used by {count} other modules)")

    print()


if __name__ == "__main__":
    example_dependency_analysis()
    example_blast_radius_analysis()
    example_path_finding()
    example_context_extraction()
    example_impact_analysis()
    example_dependency_chain()

    print("=" * 70)
    print("All query engine examples completed!")
    print("=" * 70)
