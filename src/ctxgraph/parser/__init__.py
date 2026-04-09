"""Python parsing utilities for ctxgraph.

This module provides tools to parse Python codebases and build code graphs
automatically from source files.
"""

from .ast_parser import (
    ASTParser,
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ParseResult,
    parse_python_file,
)
from .builder import GraphBuilder, build_graph
from .discovery import FileDiscovery, discover_python_files
from .resolver import SymbolResolver, path_to_module_name

__all__ = [
    # Main interfaces
    "GraphBuilder",
    "build_graph",
    # File discovery
    "FileDiscovery",
    "discover_python_files",
    # Symbol resolution
    "SymbolResolver",
    "path_to_module_name",
    # AST parsing
    "ASTParser",
    "parse_python_file",
    # Data structures
    "ParseResult",
    "ImportInfo",
    "ClassInfo",
    "FunctionInfo",
]
