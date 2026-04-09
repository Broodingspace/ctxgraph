"""ctxgraph: Transform Python codebases into queryable context graphs.

ctxgraph builds rich, queryable graphs from Python code, capturing semantic
relationships like imports, calls, inheritance, and data flow. It's designed
for AI coding assistants, documentation generators, and engineers who need to
programmatically reason about code structure.

Basic usage:
    >>> from ctxgraph import CodeGraph, Node, Edge, NodeType, EdgeType
    >>> graph = CodeGraph()
    >>> graph.add_node(Node("myapp.utils", NodeType.MODULE, "utils"))
    True
    >>> graph.add_node(Node("myapp.utils.helper", NodeType.FUNCTION, "helper"))
    True
    >>> graph.add_edge(Edge("myapp.utils", "myapp.utils.helper", EdgeType.DEFINES))
    True
    >>> print(graph.stats())
    {'total_nodes': 2, 'total_edges': 1, ...}
"""

from .graph import CodeGraph, Edge, EdgeType, Node, NodeType, SourceLocation
from .io import graph_from_dict, graph_to_dict, load_graph, save_graph
from .parser import GraphBuilder, build_graph
from .query import QueryEngine
from .retrieval import RetrievalEngine, pack_minimal_context, rank_context_for_query

__version__ = "0.1.0"

__all__ = [
    # Core graph types
    "CodeGraph",
    "Node",
    "Edge",
    "SourceLocation",
    "NodeType",
    "EdgeType",
    # IO API
    "graph_to_dict",
    "graph_from_dict",
    "save_graph",
    "load_graph",
    # Parser API
    "GraphBuilder",
    "build_graph",
    # Query API
    "QueryEngine",
    # Retrieval API
    "RetrievalEngine",
    "rank_context_for_query",
    "pack_minimal_context",
    # Version
    "__version__",
]
