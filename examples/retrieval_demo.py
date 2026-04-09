"""Example: Graph-Aware Context Retrieval for LLMs.

This example demonstrates how to use ctxgraph's retrieval engine to find
relevant code context for LLM prompts without using embeddings or vector DBs.
"""

from pathlib import Path

from ctxgraph import build_graph, pack_minimal_context, rank_context_for_query


def example_basic_retrieval() -> None:
    """Example: Basic context retrieval."""
    print("=" * 70)
    print("Example 1: Basic Context Retrieval")
    print("=" * 70)

    # Build graph of ctxgraph itself
    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    # Query for relevant code
    query = "graph node operations"
    print(f"\nQuery: '{query}'")
    print("-" * 70)

    # Rank all nodes by relevance
    result = rank_context_for_query(graph, query)

    print(f"\nFound {len(result.ranked_nodes)} relevant nodes")
    print("\nTop 5 results:")

    for i, scored in enumerate(result.ranked_nodes[:5], 1):
        print(f"\n{i}. {scored.node.id}")
        print(f"   Score: {scored.score:.2f}")
        print(f"   Type: {scored.node.type.name}")

        # Show score breakdown
        if scored.score_breakdown:
            print("   Breakdown:")
            for component, score in scored.score_breakdown.items():
                print(f"     - {component}: {score:.2f}")

    print()


def example_token_budgeting() -> None:
    """Example: Pack context within token budget."""
    print("=" * 70)
    print("Example 2: Token Budget Packing")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    # Pack context for different budgets
    budgets = [500, 1000, 2000]

    for budget in budgets:
        context = pack_minimal_context(
            graph,
            "query engine path finding",
            token_budget=budget
        )

        print(f"\nBudget: {budget} tokens")
        print(f"  Packed: {len(context.nodes)} nodes")
        print(f"  Estimated: {context.estimated_tokens} tokens")
        print(f"  Utilization: {context.utilization:.1f}%")

    # Show what was packed
    context = pack_minimal_context(
        graph,
        "query engine",
        token_budget=1000
    )

    print(f"\n\nDetailed packing (budget=1000):")
    print(f"Query: 'query engine'")
    print("\nPacked nodes:")
    for i, node in enumerate(context.nodes[:10], 1):
        print(f"  {i}. {node.id} ({node.type.name})")
    if len(context.nodes) > 10:
        print(f"  ... and {len(context.nodes) - 10} more")

    print()


def example_llm_workflow() -> None:
    """Example: Complete LLM context building workflow."""
    print("=" * 70)
    print("Example 3: LLM Context Building Workflow")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    # Scenario: LLM needs to understand how to add nodes to graph
    query = "how to add nodes to graph"

    print(f"\nScenario: '{query}'")
    print("-" * 70)

    # Step 1: Rank relevant code
    ranked = rank_context_for_query(graph, query)

    print(f"\nStep 1: Found {len(ranked.ranked_nodes)} relevant nodes")
    print(f"Top result: {ranked.top_node.node.id if ranked.top_node else 'None'}")

    # Step 2: Pack within budget
    TOKEN_BUDGET = 2000
    context = pack_minimal_context(graph, query, token_budget=TOKEN_BUDGET)

    print(f"\nStep 2: Packed context")
    print(f"  Nodes: {len(context.nodes)}")
    print(f"  Tokens: {context.estimated_tokens}/{TOKEN_BUDGET}")
    print(f"  Files: {len({n.file_path for n in context.nodes if n.file_path})}")

    # Step 3: Build LLM prompt (simulation)
    print(f"\nStep 3: LLM Prompt Structure")
    print("-" * 70)

    prompt = f"""# Task: {query}

## Context

The following code is relevant to your task:

"""

    # Add top nodes to prompt
    for node in context.nodes[:5]:
        prompt += f"\n### {node.id} ({node.type.name})\n"
        if node.metadata.get("docstring"):
            docstring = node.metadata["docstring"][:100]
            prompt += f"'''{docstring}...'''\n"
        if node.location:
            prompt += f"Location: {node.location.file_path}:{node.location.line_start}\n"

    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)

    print("\n[Full prompt would include actual code snippets]")
    print()


def example_entrypoint_biasing() -> None:
    """Example: Use entrypoints to bias search."""
    print("=" * 70)
    print("Example 4: Entrypoint Biasing")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    query = "graph operations"

    # Search without entrypoints
    result_no_entry = rank_context_for_query(graph, query)

    # Search with entrypoints (bias towards graph module)
    entrypoints = ["ctxgraph.graph.graph"]
    result_with_entry = rank_context_for_query(graph, query, entrypoints=entrypoints)

    print(f"\nQuery: '{query}'")
    print("-" * 70)

    print("\nWithout entrypoints:")
    for i, scored in enumerate(result_no_entry.ranked_nodes[:3], 1):
        print(f"  {i}. {scored.node.id} (score: {scored.score:.2f})")

    print(f"\nWith entrypoints ({entrypoints}):")
    for i, scored in enumerate(result_with_entry.ranked_nodes[:3], 1):
        print(f"  {i}. {scored.node.id} (score: {scored.score:.2f})")
        if "entrypoint" in scored.score_breakdown:
            print(f"     [entrypoint bonus: {scored.score_breakdown.get('entrypoint_bonus', 0):.2f}]")

    print("\n[Entrypoints bias search towards specific modules/areas]")
    print()


def example_comparative_search() -> None:
    """Example: Compare different query strategies."""
    print("=" * 70)
    print("Example 5: Query Strategy Comparison")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    queries = [
        "Node",  # Exact class name
        "add nodes",  # Natural language
        "graph.node",  # Path-like
        "graph data structure",  # Conceptual
    ]

    for query in queries:
        result = rank_context_for_query(graph, query)

        print(f"\nQuery: '{query}'")
        print(f"  Results: {len(result.ranked_nodes)}")

        if result.top_node:
            top = result.top_node
            print(f"  Top match: {top.node.id} (score: {top.score:.2f})")

            # Show why it ranked high
            top_components = sorted(
                top.score_breakdown.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            if top_components:
                print("  Key factors:")
                for component, score in top_components:
                    print(f"    - {component}: {score:.2f}")

    print()


def example_real_world_scenario() -> None:
    """Example: Real-world LLM prompt building."""
    print("=" * 70)
    print("Example 6: Real-World LLM Prompt Building")
    print("=" * 70)

    src_path = Path(__file__).parent.parent / "src" / "ctxgraph"
    graph = build_graph(src_path, package_name="ctxgraph")

    # Scenario: Developer asks "How do I query the graph?"
    user_question = "How do I query dependencies in the graph?"

    print(f"\nUser Question: {user_question}")
    print("-" * 70)

    # Extract keywords for search
    query = "query dependencies graph"

    # Pack relevant context
    context = pack_minimal_context(
        graph,
        query,
        token_budget=3000,
        include_neighbors=True
    )

    print(f"\nRetrieved Context:")
    print(f"  Nodes: {len(context.nodes)}")
    print(f"  Estimated tokens: {context.estimated_tokens}")
    print(f"  Utilization: {context.utilization:.1f}%")

    # Categorize retrieved nodes
    by_type = {}
    for node in context.nodes:
        if node.type not in by_type:
            by_type[node.type] = []
        by_type[node.type].append(node)

    print("\n  Retrieved by type:")
    for node_type, nodes in sorted(by_type.items(), key=lambda x: x[0].name):
        print(f"    {node_type.name}: {len(nodes)}")

    # Show key files
    files = {n.file_path for n in context.nodes if n.file_path}
    print(f"\n  Files involved: {len(files)}")
    for file in sorted(files)[:5]:
        print(f"    - {Path(file).name}")

    # Simulate LLM prompt
    print("\n" + "=" * 70)
    print("Prompt to LLM:")
    print("=" * 70)

    prompt = f"""User Question: {user_question}

Context: The codebase uses ctxgraph for analyzing Python code. Based on the
retrieved context, here are the relevant components:

"""

    # Add top 3 most relevant components
    ranked = rank_context_for_query(graph, query)
    for i, scored in enumerate(ranked.ranked_nodes[:3], 1):
        prompt += f"{i}. {scored.node.id}\n"
        if scored.node.metadata.get("docstring"):
            doc = scored.node.metadata["docstring"].split("\n")[0]
            prompt += f"   {doc}\n"

    prompt += "\nPlease explain how to use these components to query dependencies."

    print(prompt)
    print()


if __name__ == "__main__":
    example_basic_retrieval()
    example_token_budgeting()
    example_llm_workflow()
    example_entrypoint_biasing()
    example_comparative_search()
    example_real_world_scenario()

    print("=" * 70)
    print("All retrieval examples completed!")
    print("=" * 70)
