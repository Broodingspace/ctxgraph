"""Symbol resolution utilities for generating stable IDs.

This module handles conversion of file paths to module names and
generation of fully qualified symbol identifiers.
"""

from pathlib import Path


class SymbolResolver:
    """Generate stable, fully qualified IDs for Python symbols.

    This class handles conversion of file paths to module names and
    construction of hierarchical symbol IDs (e.g., package.module.Class.method).
    """

    def __init__(self, root_path: Path | str, package_name: str | None = None) -> None:
        """Initialize symbol resolver.

        Args:
            root_path: Root directory of the project/package.
            package_name: Optional top-level package name. If not provided,
                         will be inferred from root directory name.
        """
        self.root_path = Path(root_path).resolve()
        self.package_name = package_name or self.root_path.name

    def file_to_module_id(self, file_path: Path | str) -> str:
        """Convert a file path to a module identifier.

        Args:
            file_path: Absolute or relative path to a Python file.

        Returns:
            Fully qualified module name (e.g., "myapp.utils.helpers").

        Examples:
            >>> resolver = SymbolResolver("/path/to/myapp")
            >>> resolver.file_to_module_id("/path/to/myapp/utils/helpers.py")
            'myapp.utils.helpers'
            >>> resolver.file_to_module_id("/path/to/myapp/__init__.py")
            'myapp'
        """
        path = Path(file_path).resolve()

        try:
            # Get path relative to root
            relative = path.relative_to(self.root_path)
        except ValueError:
            # File is outside root, use absolute-based naming
            # This is a fallback for files outside the main package
            return self._absolute_to_module_id(path)

        # Convert path to module name
        parts = list(relative.parts)

        # Remove .py extension
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]

        # Handle __init__.py -> package name
        if parts[-1] == "__init__":
            parts = parts[:-1]

        # If we're at the root __init__.py, return just the package name
        if not parts:
            return self.package_name

        # Construct module ID
        return f"{self.package_name}.{'.'.join(parts)}"

    def _absolute_to_module_id(self, path: Path) -> str:
        """Fallback for files outside root: use filename as module ID.

        Args:
            path: Absolute path to file.

        Returns:
            Module ID based on filename.
        """
        name = path.stem
        if name == "__init__":
            # Use parent directory name
            return path.parent.name
        return name

    def make_symbol_id(
        self,
        module_id: str,
        *symbol_parts: str,
    ) -> str:
        """Construct a fully qualified symbol ID.

        Args:
            module_id: Module identifier (from file_to_module_id).
            *symbol_parts: Symbol parts (class name, method name, etc.).

        Returns:
            Fully qualified symbol ID.

        Examples:
            >>> resolver = SymbolResolver("/path/to/myapp")
            >>> resolver.make_symbol_id("myapp.utils", "Helper", "process")
            'myapp.utils.Helper.process'
            >>> resolver.make_symbol_id("myapp.utils", "helper_func")
            'myapp.utils.helper_func'
        """
        parts = [module_id] + [p for p in symbol_parts if p]
        return ".".join(parts)

    def resolve_import(
        self,
        module_id: str,
        import_target: str,
        is_relative: bool = False,
        level: int = 0,
    ) -> str:
        """Resolve an import statement to a fully qualified module ID.

        Args:
            module_id: The importing module's ID.
            import_target: The import target (e.g., "foo.bar" in "from foo.bar import baz").
            is_relative: Whether this is a relative import.
            level: Relative import level (number of dots: . = 1, .. = 2, etc.).

        Returns:
            Fully qualified module ID of the import target.

        Examples:
            >>> resolver = SymbolResolver("/path/to/myapp")
            >>> resolver.resolve_import("myapp.utils.helpers", "foo.bar")
            'foo.bar'
            >>> resolver.resolve_import("myapp.utils.helpers", "validators", True, 1)
            'myapp.utils.validators'
            >>> resolver.resolve_import("myapp.utils.helpers", "core", True, 2)
            'myapp.core'
        """
        if not is_relative:
            # Absolute import
            return import_target

        # Relative import: resolve based on current module's package
        module_parts = module_id.split(".")

        # Go up 'level' packages
        # level=1 means current package (.)
        # level=2 means parent package (..)
        if level > len(module_parts):
            # Can't go up that far, best effort
            base_parts = [self.package_name]
        else:
            base_parts = module_parts[: -level if level > 0 else len(module_parts)]

        if import_target:
            base_parts.append(import_target)

        return ".".join(base_parts)


def path_to_module_name(file_path: Path, root_path: Path) -> str:
    """Convert a file path to a Python module name.

    Args:
        file_path: Path to the Python file.
        root_path: Root directory of the project.

    Returns:
        Module name (e.g., "package.module").

    Examples:
        >>> path_to_module_name(Path("myapp/utils.py"), Path("myapp"))
        'myapp.utils'
    """
    resolver = SymbolResolver(root_path)
    return resolver.file_to_module_id(file_path)
