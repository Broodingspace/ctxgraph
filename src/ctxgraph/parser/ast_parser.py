"""AST-based parser for extracting code entities from Python source.

This module uses Python's ast module to parse source files and extract
entities like classes, functions, methods, and imports.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ImportInfo:
    """Information about an import statement.

    Attributes:
        module: The module being imported (e.g., "os.path").
        names: List of names imported from the module (empty for "import foo").
        alias: Alias for the import (e.g., "np" in "import numpy as np").
        is_relative: Whether this is a relative import.
        level: Relative import level (1 for ".", 2 for "..", etc.).
        lineno: Line number of the import statement.
    """

    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    is_relative: bool = False
    level: int = 0
    lineno: int = 0


@dataclass
class CallInfo:
    """Information about a function call site.

    Attributes:
        name: The called function or method name (unqualified).
        receiver: The object the call is made on (e.g. 'self', 'os', variable).
        qualified_name: Dotted name as it appears in source (e.g. 'self.save').
        lineno: Line number of the call.
        is_self_call: True when receiver is 'self' or 'cls'.
    """

    name: str
    receiver: str | None
    qualified_name: str
    lineno: int
    is_self_call: bool = False


@dataclass
class FunctionInfo:
    """Information about a function or method.

    Attributes:
        name: Function name.
        lineno: Starting line number.
        end_lineno: Ending line number.
        col_offset: Starting column offset.
        end_col_offset: Ending column offset.
        decorators: List of decorator names.
        is_async: Whether this is an async function.
        is_method: Whether this is a method (vs module-level function).
        docstring: Function docstring, if present.
        args: List of argument names.
        returns: Return type annotation (as string), if present.
        calls: Calls made inside this function body.
    """

    name: str
    lineno: int
    end_lineno: int
    col_offset: int = 0
    end_col_offset: int = 0
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    docstring: str | None = None
    args: list[str] = field(default_factory=list)
    returns: str | None = None
    calls: list[CallInfo] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a class definition.

    Attributes:
        name: Class name.
        bases: List of base class names.
        lineno: Starting line number.
        end_lineno: Ending line number.
        col_offset: Starting column offset.
        end_col_offset: Ending column offset.
        decorators: List of decorator names.
        docstring: Class docstring, if present.
        methods: List of methods defined in this class.
    """

    name: str
    bases: list[str]
    lineno: int
    end_lineno: int
    col_offset: int = 0
    end_col_offset: int = 0
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ParseResult:
    """Result of parsing a Python source file.

    Attributes:
        file_path: Path to the parsed file.
        imports: List of import statements.
        classes: List of class definitions.
        functions: List of top-level functions.
        module_docstring: Module-level docstring, if present.
        errors: List of error messages encountered during parsing.
    """

    file_path: Path
    imports: list[ImportInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    module_docstring: str | None = None
    errors: list[str] = field(default_factory=list)


class ASTParser:
    """Parse Python source files using AST.

    This parser extracts high-level entities (imports, classes, functions)
    from Python source code without executing it.
    """

    def __init__(self) -> None:
        """Initialize the AST parser."""
        pass

    def parse_file(self, file_path: Path | str) -> ParseResult:
        """Parse a Python source file.

        Args:
            file_path: Path to the Python file to parse.

        Returns:
            ParseResult containing extracted entities and any errors.

        Examples:
            >>> parser = ASTParser()
            >>> result = parser.parse_file("mymodule.py")
            >>> len(result.classes) >= 0
            True
        """
        path = Path(file_path)
        result = ParseResult(file_path=path)

        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            result.errors.append(f"Failed to read file: {e}")
            return result

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            result.errors.append(f"Syntax error: {e}")
            return result

        # Extract module docstring
        result.module_docstring = ast.get_docstring(tree)

        # Walk the AST and extract entities
        self._extract_entities(tree, result)

        return result

    def _extract_entities(self, tree: ast.Module, result: ParseResult) -> None:
        """Extract entities from the AST.

        Args:
            tree: Parsed AST module.
            result: ParseResult to populate.
        """
        for node in ast.walk(tree):
            # Extract imports
            if isinstance(node, ast.Import):
                result.imports.extend(self._extract_import(node))
            elif isinstance(node, ast.ImportFrom):
                result.imports.extend(self._extract_import_from(node))

        # Extract top-level classes and functions (don't use walk, use iter_child_nodes)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                result.classes.append(self._extract_class(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function(node)
                func_info.is_method = False
                result.functions.append(func_info)

    def _extract_import(self, node: ast.Import) -> list[ImportInfo]:
        """Extract information from an import statement.

        Args:
            node: ast.Import node.

        Returns:
            List of ImportInfo objects (one per imported name).
        """
        imports = []
        for alias in node.names:
            imports.append(
                ImportInfo(
                    module=alias.name,
                    names=[],
                    alias=alias.asname,
                    is_relative=False,
                    level=0,
                    lineno=node.lineno,
                )
            )
        return imports

    def _extract_import_from(self, node: ast.ImportFrom) -> list[ImportInfo]:
        """Extract information from a 'from ... import ...' statement.

        Args:
            node: ast.ImportFrom node.

        Returns:
            List of ImportInfo objects.
        """
        module = node.module or ""
        level = node.level or 0
        is_relative = level > 0

        # Handle different import forms
        names = []
        aliases = {}
        for alias in node.names:
            names.append(alias.name)
            if alias.asname:
                aliases[alias.name] = alias.asname

        # Create one ImportInfo per import statement
        # (or split per name if we want finer granularity)
        return [
            ImportInfo(
                module=module,
                names=names,
                alias=aliases.get(names[0]) if len(names) == 1 else None,
                is_relative=is_relative,
                level=level,
                lineno=node.lineno,
            )
        ]

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract information from a class definition.

        Args:
            node: ast.ClassDef node.

        Returns:
            ClassInfo object.
        """
        # Extract base class names
        bases = []
        for base in node.bases:
            base_name = self._get_name_from_node(base)
            if base_name:
                bases.append(base_name)

        # Extract decorators
        decorators = [self._get_name_from_node(dec) for dec in node.decorator_list]
        decorators = [d for d in decorators if d]  # Filter out None values

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function(item)
                func_info.is_method = True
                methods.append(func_info)

        return ClassInfo(
            name=node.name,
            bases=bases,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            col_offset=node.col_offset,
            end_col_offset=node.end_col_offset or 0,
            decorators=decorators,
            docstring=docstring,
            methods=methods,
        )

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> FunctionInfo:
        """Extract information from a function or method definition.

        Args:
            node: ast.FunctionDef or ast.AsyncFunctionDef node.

        Returns:
            FunctionInfo object.
        """
        # Extract decorators
        decorators = [self._get_name_from_node(dec) for dec in node.decorator_list]
        decorators = [d for d in decorators if d]

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract arguments
        args = [arg.arg for arg in node.args.args]

        # Extract return type annotation
        returns = None
        if node.returns:
            returns = self._get_name_from_node(node.returns)

        # Extract calls made inside the function body
        calls = self._extract_calls(node)

        return FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            col_offset=node.col_offset,
            end_col_offset=node.end_col_offset or 0,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=docstring,
            args=args,
            returns=returns,
            calls=calls,
        )

    def _extract_calls(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[CallInfo]:
        """Extract all call sites from a function body.

        Handles three common patterns:
        - Direct calls:         ``foo()``
        - Self/cls calls:       ``self.method()`` / ``cls.method()``
        - Module-qualified:     ``os.path.join()`` / ``helper.do()``

        Nested function definitions are not recursed into — their calls
        are attributed to those inner functions, not the outer one.

        Args:
            func_node: The function AST node to analyse.

        Returns:
            List of CallInfo objects for each call site found.
        """
        calls: list[CallInfo] = []
        SELF_NAMES = {"self", "cls"}

        for node in ast.walk(func_node):
            # Skip nested function/class bodies — they get their own FunctionInfo
            if node is not func_node and isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue

            if not isinstance(node, ast.Call):
                continue

            call_node = node
            func = call_node.func

            if isinstance(func, ast.Name):
                # Simple call: foo()
                calls.append(
                    CallInfo(
                        name=func.id,
                        receiver=None,
                        qualified_name=func.id,
                        lineno=call_node.lineno,
                        is_self_call=False,
                    )
                )

            elif isinstance(func, ast.Attribute):
                # Attribute call: self.save() / os.path.join() / obj.method()
                receiver = None
                if isinstance(func.value, ast.Name):
                    receiver = func.value.id

                qualified = self._get_name_from_node(func) or func.attr
                is_self = receiver in SELF_NAMES

                calls.append(
                    CallInfo(
                        name=func.attr,
                        receiver=receiver,
                        qualified_name=qualified,
                        lineno=call_node.lineno,
                        is_self_call=is_self,
                    )
                )

        return calls

    def _get_name_from_node(self, node: ast.AST) -> str | None:
        """Extract a name from an AST node.

        This handles various node types to extract meaningful names
        (e.g., from attributes, function calls, etc.).

        Args:
            node: AST node to extract name from.

        Returns:
            Extracted name, or None if unable to extract.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # e.g., foo.bar.baz -> "foo.bar.baz"
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts)) if parts else None
        elif isinstance(node, ast.Subscript):
            # e.g., List[int] -> "List"
            return self._get_name_from_node(node.value)
        elif isinstance(node, ast.Call):
            # e.g., decorator() -> "decorator"
            return self._get_name_from_node(node.func)
        elif isinstance(node, ast.Constant):
            # Handle string constants (rare but possible)
            return str(node.value)
        else:
            # For complex expressions, return a placeholder or None
            return None


def parse_python_file(file_path: Path | str) -> ParseResult:
    """Convenience function to parse a Python file.

    Args:
        file_path: Path to the Python file.

    Returns:
        ParseResult with extracted entities.

    Examples:
        >>> result = parse_python_file("mymodule.py")
        >>> result.file_path.suffix
        '.py'
    """
    parser = ASTParser()
    return parser.parse_file(file_path)
