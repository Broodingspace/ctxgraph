"""File discovery utilities for Python codebases.

This module provides functionality to discover Python source files in a
directory tree, with support for filtering and exclusion patterns.
"""

from pathlib import Path
from typing import Iterator


class FileDiscovery:
    """Discover Python files in a directory tree.

    This class handles traversal of directory structures to find Python
    source files, with built-in filtering for common directories that
    should be excluded (e.g., virtual environments, build directories).
    """

    # Directories to exclude by default
    DEFAULT_EXCLUDES = {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "env",
        "ENV",
        "build",
        "dist",
        "*.egg-info",
        "node_modules",
        ".eggs",
    }

    def __init__(
        self,
        root_path: Path | str,
        exclude_dirs: set[str] | None = None,
        include_tests: bool = True,
    ) -> None:
        """Initialize file discovery.

        Args:
            root_path: Root directory to start discovery from.
            exclude_dirs: Additional directory names to exclude (merged with defaults).
            include_tests: Whether to include test files (default: True).
        """
        self.root_path = Path(root_path).resolve()
        self.exclude_dirs = self.DEFAULT_EXCLUDES.copy()
        if exclude_dirs:
            self.exclude_dirs.update(exclude_dirs)
        self.include_tests = include_tests

    def discover(self) -> list[Path]:
        """Discover all Python files in the directory tree.

        Returns:
            List of absolute paths to Python files.

        Examples:
            >>> discovery = FileDiscovery("/path/to/project")
            >>> files = discovery.discover()
            >>> len(files) > 0
            True
        """
        return list(self._walk())

    def _walk(self) -> Iterator[Path]:
        """Walk the directory tree and yield Python files.

        Yields:
            Absolute paths to Python files.
        """
        if not self.root_path.exists():
            return

        if self.root_path.is_file():
            # Single file provided
            if self._should_include_file(self.root_path):
                yield self.root_path
            return

        # Directory traversal
        for path in self.root_path.rglob("*.py"):
            if self._should_include_file(path):
                yield path

    def _should_include_file(self, path: Path) -> bool:
        """Check if a file should be included in discovery.

        Args:
            path: Path to check.

        Returns:
            True if the file should be included.
        """
        # Check if any parent directory is excluded
        for part in path.parts:
            if part in self.exclude_dirs:
                return False

        # Optionally exclude test files
        if not self.include_tests and self._is_test_file(path):
            return False

        return True

    @staticmethod
    def _is_test_file(path: Path) -> bool:
        """Check if a file appears to be a test file.

        Args:
            path: Path to check.

        Returns:
            True if the file looks like a test file.
        """
        name = path.name
        return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def discover_python_files(
    root_path: Path | str,
    exclude_dirs: set[str] | None = None,
    include_tests: bool = True,
) -> list[Path]:
    """Convenience function to discover Python files.

    Args:
        root_path: Root directory to start discovery from.
        exclude_dirs: Directory names to exclude (beyond defaults).
        include_tests: Whether to include test files.

    Returns:
        List of absolute paths to Python files.

    Examples:
        >>> files = discover_python_files("/path/to/project")
        >>> all(f.suffix == ".py" for f in files)
        True
    """
    discovery = FileDiscovery(root_path, exclude_dirs, include_tests)
    return discovery.discover()
