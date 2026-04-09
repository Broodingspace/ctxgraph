"""Basic usage examples for ctxgraph.

This script demonstrates how to:
1. Create a code graph
2. Add nodes representing code entities
3. Add edges representing relationships
4. Query the graph for information
5. Traverse the graph to understand code structure
"""

from ctxgraph import CodeGraph, Edge, EdgeType, Node, NodeType, SourceLocation


def example_simple_module() -> None:
    """Example: Build a graph for a simple module with functions."""
    print("=" * 60)
    print("Example 1: Simple Module Graph")
    print("=" * 60)

    # Create an empty graph
    graph = CodeGraph()

    # Add a module node
    utils_module = Node(
        id="myapp.utils",
        type=NodeType.MODULE,
        name="utils",
        location=SourceLocation(file_path="myapp/utils.py", line_start=1, line_end=50),
        metadata={"docstring": "Utility functions for myapp"},
    )
    graph.add_node(utils_module)

    # Add function nodes
    helper_func = Node(
        id="myapp.utils.helper",
        type=NodeType.FUNCTION,
        name="helper",
        location=SourceLocation(file_path="myapp/utils.py", line_start=10, line_end=15),
        metadata={"docstring": "A helper function", "is_async": False},
    )
    graph.add_node(helper_func)

    validator_func = Node(
        id="myapp.utils.validate",
        type=NodeType.FUNCTION,
        name="validate",
        location=SourceLocation(file_path="myapp/utils.py", line_start=17, line_end=25),
        metadata={"docstring": "Validates input", "is_async": False},
    )
    graph.add_node(validator_func)

    # Add edges showing that the module defines these functions
    graph.add_edge(Edge("myapp.utils", "myapp.utils.helper", EdgeType.DEFINES))
    graph.add_edge(Edge("myapp.utils", "myapp.utils.validate", EdgeType.DEFINES))

    # Add edge showing that helper calls validate
    graph.add_edge(
        Edge(
            "myapp.utils.helper",
            "myapp.utils.validate",
            EdgeType.CALLS,
            metadata={"call_count": 1, "line": 13},
        )
    )

    # Query the graph
    print(f"\nGraph stats: {graph.stats()}")
    print(f"Total nodes: {graph.node_count}")
    print(f"Total edges: {graph.edge_count}")

    # Find all functions
    print("\nAll functions:")
    for node in graph.nodes(node_type=NodeType.FUNCTION):
        print(f"  - {node.name} ({node.id})")

    # Find what the module defines
    print("\nWhat does myapp.utils define?")
    defined_entities = graph.get_neighbors("myapp.utils", edge_type=EdgeType.DEFINES)
    for entity in defined_entities:
        print(f"  - {entity.type.name}: {entity.name}")

    # Find what helper function calls
    print("\nWhat does helper() call?")
    called_funcs = graph.get_neighbors(
        "myapp.utils.helper", edge_type=EdgeType.CALLS, direction="outgoing"
    )
    for func in called_funcs:
        print(f"  - {func.name}")

    print()


def example_class_hierarchy() -> None:
    """Example: Build a graph with class inheritance."""
    print("=" * 60)
    print("Example 2: Class Hierarchy Graph")
    print("=" * 60)

    graph = CodeGraph()

    # Add module
    models_module = Node(
        id="myapp.models",
        type=NodeType.MODULE,
        name="models",
        location=SourceLocation(file_path="myapp/models.py", line_start=1, line_end=100),
    )
    graph.add_node(models_module)

    # Add base class
    base_class = Node(
        id="myapp.models.BaseModel",
        type=NodeType.CLASS,
        name="BaseModel",
        location=SourceLocation(file_path="myapp/models.py", line_start=5, line_end=20),
        metadata={"is_abstract": True},
    )
    graph.add_node(base_class)

    # Add derived classes
    user_class = Node(
        id="myapp.models.User",
        type=NodeType.CLASS,
        name="User",
        location=SourceLocation(file_path="myapp/models.py", line_start=23, line_end=45),
    )
    graph.add_node(user_class)

    product_class = Node(
        id="myapp.models.Product",
        type=NodeType.CLASS,
        name="Product",
        location=SourceLocation(file_path="myapp/models.py", line_start=48, line_end=70),
    )
    graph.add_node(product_class)

    # Add method nodes
    user_save = Node(
        id="myapp.models.User.save",
        type=NodeType.FUNCTION,
        name="save",
        location=SourceLocation(file_path="myapp/models.py", line_start=35, line_end=42),
        metadata={"is_method": True, "is_async": True},
    )
    graph.add_node(user_save)

    # Define relationships
    graph.add_edge(Edge("myapp.models", "myapp.models.BaseModel", EdgeType.DEFINES))
    graph.add_edge(Edge("myapp.models", "myapp.models.User", EdgeType.DEFINES))
    graph.add_edge(Edge("myapp.models", "myapp.models.Product", EdgeType.DEFINES))
    graph.add_edge(Edge("myapp.models.User", "myapp.models.User.save", EdgeType.CONTAINS))

    # Inheritance edges
    graph.add_edge(Edge("myapp.models.User", "myapp.models.BaseModel", EdgeType.INHERITS))
    graph.add_edge(Edge("myapp.models.Product", "myapp.models.BaseModel", EdgeType.INHERITS))

    # Query inheritance hierarchy
    print("\nClasses defined in myapp.models:")
    for node in graph.nodes(node_type=NodeType.CLASS):
        print(f"  - {node.name}")

    print("\nWhat inherits from BaseModel?")
    # Find all classes that inherit from BaseModel (incoming edges)
    subclasses = graph.get_neighbors(
        "myapp.models.BaseModel", edge_type=EdgeType.INHERITS, direction="incoming"
    )
    for cls in subclasses:
        print(f"  - {cls.name}")

    print("\nWhat does User inherit from?")
    parent_classes = graph.get_neighbors(
        "myapp.models.User", edge_type=EdgeType.INHERITS, direction="outgoing"
    )
    for cls in parent_classes:
        print(f"  - {cls.name}")

    print()


def example_import_graph() -> None:
    """Example: Build a module import graph."""
    print("=" * 60)
    print("Example 3: Module Import Graph")
    print("=" * 60)

    graph = CodeGraph()

    # Add modules
    main_mod = Node("myapp.main", NodeType.MODULE, "main")
    utils_mod = Node("myapp.utils", NodeType.MODULE, "utils")
    models_mod = Node("myapp.models", NodeType.MODULE, "models")
    db_mod = Node("myapp.db", NodeType.MODULE, "db")

    for mod in [main_mod, utils_mod, models_mod, db_mod]:
        graph.add_node(mod)

    # Add import relationships
    # main imports utils and models
    graph.add_edge(
        Edge(
            "myapp.main",
            "myapp.utils",
            EdgeType.IMPORTS,
            metadata={"imported_names": ["helper", "validate"]},
        )
    )
    graph.add_edge(
        Edge(
            "myapp.main",
            "myapp.models",
            EdgeType.IMPORTS,
            metadata={"imported_names": ["User", "Product"]},
        )
    )

    # models imports db
    graph.add_edge(
        Edge("myapp.models", "myapp.db", EdgeType.IMPORTS, metadata={"import_type": "module"})
    )

    # utils imports models (creating a cycle with main)
    graph.add_edge(Edge("myapp.utils", "myapp.models", EdgeType.IMPORTS))

    print("\nModule dependencies:")
    for mod_node in graph.nodes(node_type=NodeType.MODULE):
        dependencies = graph.get_neighbors(
            mod_node.id, edge_type=EdgeType.IMPORTS, direction="outgoing"
        )
        if dependencies:
            print(f"  {mod_node.name} imports:")
            for dep in dependencies:
                # Get edge to see metadata
                edge = graph.get_edge(mod_node.id, dep.id, EdgeType.IMPORTS)
                if edge and "imported_names" in edge.metadata:
                    names = ", ".join(edge.metadata["imported_names"])
                    print(f"    - {dep.name} ({names})")
                else:
                    print(f"    - {dep.name}")

    print("\nWhat imports myapp.models?")
    importers = graph.get_neighbors(
        "myapp.models", edge_type=EdgeType.IMPORTS, direction="incoming"
    )
    for importer in importers:
        print(f"  - {importer.name}")

    print()


def example_graph_traversal() -> None:
    """Example: Advanced graph traversal and queries."""
    print("=" * 60)
    print("Example 4: Graph Traversal and Queries")
    print("=" * 60)

    graph = CodeGraph()

    # Build a small call graph: main -> process -> validate, save
    nodes = [
        Node("app.main", NodeType.FUNCTION, "main"),
        Node("app.process", NodeType.FUNCTION, "process"),
        Node("app.validate", NodeType.FUNCTION, "validate"),
        Node("app.save", NodeType.FUNCTION, "save"),
    ]

    for node in nodes:
        graph.add_node(node)

    graph.add_edge(Edge("app.main", "app.process", EdgeType.CALLS))
    graph.add_edge(Edge("app.process", "app.validate", EdgeType.CALLS))
    graph.add_edge(Edge("app.process", "app.save", EdgeType.CALLS))

    print("\nDirect callees of process:")
    callees = graph.get_neighbors("app.process", edge_type=EdgeType.CALLS, direction="outgoing")
    for callee in callees:
        print(f"  - {callee.name}")

    print("\nDirect callers of process:")
    callers = graph.get_neighbors("app.process", edge_type=EdgeType.CALLS, direction="incoming")
    for caller in callers:
        print(f"  - {caller.name}")

    print("\nAll edges from process:")
    for edge in graph.get_outgoing_edges("app.process"):
        target = graph.get_node(edge.target_id)
        print(f"  - {edge.type.name} -> {target.name if target else edge.target_id}")

    print()


def example_metadata_usage() -> None:
    """Example: Using metadata for rich node/edge information."""
    print("=" * 60)
    print("Example 5: Metadata Usage")
    print("=" * 60)

    graph = CodeGraph()

    # Create a node with rich metadata
    func = Node(
        id="api.handlers.get_user",
        type=NodeType.FUNCTION,
        name="get_user",
        location=SourceLocation(
            file_path="api/handlers.py", line_start=42, line_end=58, column_start=0, column_end=4
        ),
        metadata={
            "docstring": "Retrieve user by ID from database",
            "is_async": True,
            "decorators": ["@router.get('/users/{user_id}')", "@requires_auth"],
            "return_type": "User | None",
            "complexity": 5,
        },
    )
    graph.add_node(func)

    # Add metadata dynamically
    enriched = func.with_metadata(last_modified="2024-03-15", author="alice@example.com")
    graph.add_node(enriched)  # This won't add (same ID), but demonstrates the pattern

    # Query node and access metadata
    node = graph.get_node("api.handlers.get_user")
    if node:
        print(f"\nFunction: {node.name}")
        print(f"Location: {node.location.file_path}:{node.location.line_start}")
        print(f"Is async: {node.metadata.get('is_async', False)}")
        print(f"Decorators: {node.metadata.get('decorators', [])}")
        print(f"Docstring: {node.metadata.get('docstring', 'N/A')}")
        print(f"Complexity: {node.metadata.get('complexity', 'unknown')}")

    print()


if __name__ == "__main__":
    example_simple_module()
    example_class_hierarchy()
    example_import_graph()
    example_graph_traversal()
    example_metadata_usage()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
