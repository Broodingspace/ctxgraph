"""Graph builder for Python codebases.

This module orchestrates file discovery, parsing, and graph construction
to build a complete CodeGraph from a Python codebase.
"""

from pathlib import Path

from ..graph import CodeGraph, Edge, EdgeType, Node, NodeType, SourceLocation
from .ast_parser import ASTParser, CallInfo, ClassInfo, FunctionInfo, ImportInfo, ParseResult
from .discovery import FileDiscovery
from .resolver import SymbolResolver


class GraphBuilder:
    """Build a CodeGraph from a Python codebase.

    This class orchestrates the entire process:
    1. Discover Python files
    2. Parse each file with AST
    3. Generate stable symbol IDs
    4. Build nodes and edges in the graph
    """

    def __init__(
        self,
        root_path: Path | str,
        package_name: str | None = None,
        exclude_dirs: set[str] | None = None,
        include_tests: bool = True,
    ) -> None:
        """Initialize graph builder.

        Args:
            root_path: Root directory of the codebase.
            package_name: Top-level package name (inferred from root if not provided).
            exclude_dirs: Additional directories to exclude from discovery.
            include_tests: Whether to include test files.
        """
        self.root_path = Path(root_path).resolve()
        self.package_name = package_name

        # Initialize components
        self.discovery = FileDiscovery(root_path, exclude_dirs, include_tests)
        self.resolver = SymbolResolver(root_path, package_name)
        self.parser = ASTParser()

        # Build state
        self.graph = CodeGraph()
        self.parse_results: dict[str, ParseResult] = {}  # module_id -> ParseResult

    def build(self) -> CodeGraph:
        """Build the complete code graph.

        Returns:
            CodeGraph with nodes and edges for the entire codebase.

        Examples:
            >>> builder = GraphBuilder("/path/to/project")
            >>> graph = builder.build()
            >>> graph.node_count > 0
            True
        """
        # Step 1: Discover files
        files = self.discovery.discover()

        # Step 2: Parse all files and create module nodes
        for file_path in files:
            self._parse_and_add_module(file_path)

        # Step 3: Add edges based on relationships
        self._build_relationships()

        return self.graph

    def _parse_and_add_module(self, file_path: Path) -> None:
        """Parse a file and add module node to graph.

        Args:
            file_path: Path to Python file.
        """
        # Parse the file
        result = self.parser.parse_file(file_path)

        # Generate module ID
        module_id = self.resolver.file_to_module_id(file_path)
        self.parse_results[module_id] = result

        # Create module node
        module_node = Node(
            id=module_id,
            type=NodeType.MODULE,
            name=file_path.stem if file_path.stem != "__init__" else file_path.parent.name,
            location=SourceLocation(
                file_path=str(file_path),
                line_start=1,
                line_end=self._count_lines(file_path),
            ),
            metadata={
                "docstring": result.module_docstring,
                "file_path": str(file_path),
                "has_errors": len(result.errors) > 0,
            },
        )
        self.graph.add_node(module_node)

        # Add class nodes
        for class_info in result.classes:
            self._add_class_node(module_id, class_info, file_path)

        # Add function nodes
        for func_info in result.functions:
            self._add_function_node(module_id, func_info, file_path)

    def _add_class_node(
        self, module_id: str, class_info: ClassInfo, file_path: Path
    ) -> None:
        """Add a class node and its methods to the graph.

        Args:
            module_id: ID of the containing module.
            class_info: Parsed class information.
            file_path: Path to the source file.
        """
        class_id = self.resolver.make_symbol_id(module_id, class_info.name)

        # Create class node
        class_node = Node(
            id=class_id,
            type=NodeType.CLASS,
            name=class_info.name,
            location=SourceLocation(
                file_path=str(file_path),
                line_start=class_info.lineno,
                line_end=class_info.end_lineno,
                column_start=class_info.col_offset,
                column_end=class_info.end_col_offset,
            ),
            metadata={
                "docstring": class_info.docstring,
                "decorators": class_info.decorators,
                "base_classes": class_info.bases,
            },
        )
        self.graph.add_node(class_node)

        # Add DEFINES edge from module to class
        self.graph.add_edge(Edge(module_id, class_id, EdgeType.DEFINES))

        # Add CONTAINS edge from module to class
        self.graph.add_edge(Edge(module_id, class_id, EdgeType.CONTAINS))

        # Add method nodes
        for method_info in class_info.methods:
            self._add_method_node(class_id, method_info, file_path)

    def _add_method_node(
        self, class_id: str, method_info: FunctionInfo, file_path: Path
    ) -> None:
        """Add a method node to the graph.

        Args:
            class_id: ID of the containing class.
            method_info: Parsed method information.
            file_path: Path to the source file.
        """
        method_id = self.resolver.make_symbol_id(class_id, method_info.name)

        method_node = Node(
            id=method_id,
            type=NodeType.FUNCTION,
            name=method_info.name,
            location=SourceLocation(
                file_path=str(file_path),
                line_start=method_info.lineno,
                line_end=method_info.end_lineno,
                column_start=method_info.col_offset,
                column_end=method_info.end_col_offset,
            ),
            metadata={
                "docstring": method_info.docstring,
                "decorators": method_info.decorators,
                "is_async": method_info.is_async,
                "is_method": True,
                "args": method_info.args,
                "returns": method_info.returns,
            },
        )
        self.graph.add_node(method_node)

        # Add CONTAINS edge from class to method
        self.graph.add_edge(Edge(class_id, method_id, EdgeType.CONTAINS))

        # Add DEFINES edge from class to method
        self.graph.add_edge(Edge(class_id, method_id, EdgeType.DEFINES))

    def _add_function_node(
        self, module_id: str, func_info: FunctionInfo, file_path: Path
    ) -> None:
        """Add a function node to the graph.

        Args:
            module_id: ID of the containing module.
            func_info: Parsed function information.
            file_path: Path to the source file.
        """
        func_id = self.resolver.make_symbol_id(module_id, func_info.name)

        func_node = Node(
            id=func_id,
            type=NodeType.FUNCTION,
            name=func_info.name,
            location=SourceLocation(
                file_path=str(file_path),
                line_start=func_info.lineno,
                line_end=func_info.end_lineno,
                column_start=func_info.col_offset,
                column_end=func_info.end_col_offset,
            ),
            metadata={
                "docstring": func_info.docstring,
                "decorators": func_info.decorators,
                "is_async": func_info.is_async,
                "is_method": False,
                "args": func_info.args,
                "returns": func_info.returns,
            },
        )
        self.graph.add_node(func_node)

        # Add DEFINES edge from module to function
        self.graph.add_edge(Edge(module_id, func_id, EdgeType.DEFINES))

        # Add CONTAINS edge from module to function
        self.graph.add_edge(Edge(module_id, func_id, EdgeType.CONTAINS))

    def _build_relationships(self) -> None:
        """Build relationship edges (imports, inheritance, calls) in the graph."""
        for module_id, result in self.parse_results.items():
            # Add import edges
            for import_info in result.imports:
                self._add_import_edge(module_id, import_info)

            # Add inheritance edges
            for class_info in result.classes:
                self._add_inheritance_edges(module_id, class_info)

        # Call edges need the full graph to be built first (all nodes must exist)
        for module_id, result in self.parse_results.items():
            self._build_call_edges(module_id, result)

    def _build_call_edges(self, module_id: str, result: ParseResult) -> None:
        """Add CALLS edges for all functions and methods in a module.

        Uses a conservative resolution strategy:
        1. self.method()  → resolve within the same class
        2. name()         → look in same module first, then imported symbols
        3. module.name()  → resolve via import table

        Args:
            module_id: ID of the module being analysed.
            result: Parse result for that module.
        """
        # Build a lookup table: imported symbol name → resolved module node id
        # e.g. "from .db import Connection" → "sample_project.db"
        import_map: dict[str, str] = {}
        for imp in result.imports:
            target_module_id = self.resolver.resolve_import(
                module_id, imp.module, imp.is_relative, imp.level
            )
            if self.graph.has_node(target_module_id):
                # Map each imported name to the target module
                for name in imp.names:
                    import_map[name] = target_module_id
                # Also map the module alias itself (import os as o → o → os)
                if imp.alias:
                    import_map[imp.alias] = target_module_id
                elif imp.module:
                    # import foo.bar → foo accessible as foo
                    top = imp.module.split(".")[0]
                    import_map[top] = target_module_id

        # Process module-level functions
        for func_info in result.functions:
            caller_id = self.resolver.make_symbol_id(module_id, func_info.name)
            if not self.graph.has_node(caller_id):
                continue
            for call in func_info.calls:
                self._resolve_and_add_call_edge(
                    caller_id, call, module_id, None, import_map
                )

        # Process class methods
        for class_info in result.classes:
            class_id = self.resolver.make_symbol_id(module_id, class_info.name)
            for method_info in class_info.methods:
                caller_id = self.resolver.make_symbol_id(class_id, method_info.name)
                if not self.graph.has_node(caller_id):
                    continue
                for call in method_info.calls:
                    self._resolve_and_add_call_edge(
                        caller_id, call, module_id, class_id, import_map
                    )

    def _resolve_and_add_call_edge(
        self,
        caller_id: str,
        call: CallInfo,
        module_id: str,
        class_id: str | None,
        import_map: dict[str, str],
    ) -> None:
        """Attempt to resolve a call site to a known node and add a CALLS edge.

        Args:
            caller_id: Graph node ID of the calling function.
            call: Extracted call information.
            module_id: Module containing the caller.
            class_id: Class containing the caller (None for module-level functions).
            import_map: Map from imported name to resolved module node ID.
        """
        callee_id: str | None = None

        if call.is_self_call and class_id:
            # self.method() → look for sibling method in same class
            candidate = self.resolver.make_symbol_id(class_id, call.name)
            if self.graph.has_node(candidate):
                callee_id = candidate

        elif call.receiver and call.receiver in import_map:
            # module.func() → receiver is an imported module
            target_module = import_map[call.receiver]
            candidate = self.resolver.make_symbol_id(target_module, call.name)
            if self.graph.has_node(candidate):
                callee_id = candidate

        elif call.receiver is None:
            # foo() — bare call: check same module, then imported names
            candidate = self.resolver.make_symbol_id(module_id, call.name)
            if self.graph.has_node(candidate):
                callee_id = candidate
            elif call.name in import_map:
                # Could be a class imported directly (e.g. User())
                target_module = import_map[call.name]
                candidate = self.resolver.make_symbol_id(target_module, call.name)
                if self.graph.has_node(candidate):
                    callee_id = candidate

        if callee_id and callee_id != caller_id:
            try:
                self.graph.add_edge(
                    Edge(
                        caller_id,
                        callee_id,
                        EdgeType.CALLS,
                        metadata={"lineno": call.lineno},
                    )
                )
            except ValueError:
                pass  # Either endpoint missing — skip silently

    def _add_import_edge(self, module_id: str, import_info: ImportInfo) -> None:
        """Add an import edge to the graph.

        Args:
            module_id: ID of the importing module.
            import_info: Information about the import.
        """
        # Resolve the import to a module ID
        target_module_id = self.resolver.resolve_import(
            module_id,
            import_info.module,
            import_info.is_relative,
            import_info.level,
        )

        # Check if target module exists in graph (may be external/stdlib)
        # For now, create edge only if we know about the module
        # In future, could create placeholder nodes for external modules
        if not self.graph.has_node(target_module_id):
            # External import - optionally create a placeholder node
            # For v1, we'll skip external imports to keep graph clean
            return

        # Create import edge
        edge = Edge(
            module_id,
            target_module_id,
            EdgeType.IMPORTS,
            metadata={
                "imported_names": import_info.names,
                "alias": import_info.alias,
                "lineno": import_info.lineno,
            },
        )
        self.graph.add_edge(edge)

    def _add_inheritance_edges(self, module_id: str, class_info: ClassInfo) -> None:
        """Add inheritance edges for a class.

        Args:
            module_id: ID of the module containing the class.
            class_info: Information about the class.
        """
        class_id = self.resolver.make_symbol_id(module_id, class_info.name)

        for base_name in class_info.bases:
            # Try to resolve the base class
            # This is simplified - in reality we'd need to track imports
            # to fully resolve base class names
            base_id = self._resolve_base_class(module_id, base_name)

            if base_id and self.graph.has_node(base_id):
                # Add inheritance edge
                edge = Edge(class_id, base_id, EdgeType.INHERITS)
                self.graph.add_edge(edge)

    def _resolve_base_class(self, module_id: str, base_name: str) -> str | None:
        """Attempt to resolve a base class name to a fully qualified ID.

        Args:
            module_id: Module containing the class.
            base_name: Name of the base class (may be qualified or simple).

        Returns:
            Fully qualified base class ID, or None if can't resolve.
        """
        # If base_name contains dots, it's already partially qualified
        if "." in base_name:
            # Could be a full path or an import alias
            # For v1, just return as-is
            return base_name

        # Try to find in the same module first
        same_module_id = self.resolver.make_symbol_id(module_id, base_name)
        if self.graph.has_node(same_module_id):
            return same_module_id

        # Could search through imports to resolve, but that's complex
        # For v1, we'll just use the base_name as-is and it may not resolve
        return None

    @staticmethod
    def _count_lines(file_path: Path) -> int:
        """Count lines in a file.

        Args:
            file_path: Path to file.

        Returns:
            Number of lines in the file (minimum 1).
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                count = sum(1 for _ in f)
                return max(count, 1)  # At least 1 line
        except (OSError, UnicodeDecodeError):
            return 1  # Fallback


def build_graph(
    root_path: Path | str,
    package_name: str | None = None,
    exclude_dirs: set[str] | None = None,
    include_tests: bool = True,
) -> CodeGraph:
    """Convenience function to build a code graph from a Python codebase.

    Args:
        root_path: Root directory of the codebase.
        package_name: Top-level package name (inferred if not provided).
        exclude_dirs: Additional directories to exclude.
        include_tests: Whether to include test files.

    Returns:
        CodeGraph representing the codebase.

    Examples:
        >>> graph = build_graph("/path/to/myproject")
        >>> graph.node_count > 0
        True
    """
    builder = GraphBuilder(root_path, package_name, exclude_dirs, include_tests)
    return builder.build()
