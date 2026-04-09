"""Tests for symbol resolver module."""

from pathlib import Path

import pytest

from ctxgraph.parser import SymbolResolver

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


class TestSymbolResolver:
    """Test symbol resolution functionality."""

    def test_file_to_module_id(self) -> None:
        """Test converting file path to module ID."""
        resolver = SymbolResolver(SAMPLE_PROJECT, "sample_project")

        utils_file = SAMPLE_PROJECT / "utils.py"
        module_id = resolver.file_to_module_id(utils_file)

        assert module_id == "sample_project.utils"

    def test_init_file_to_module_id(self) -> None:
        """Test converting __init__.py to module ID."""
        resolver = SymbolResolver(SAMPLE_PROJECT, "sample_project")

        init_file = SAMPLE_PROJECT / "__init__.py"
        module_id = resolver.file_to_module_id(init_file)

        assert module_id == "sample_project"

    def test_make_symbol_id(self) -> None:
        """Test constructing symbol IDs."""
        resolver = SymbolResolver(SAMPLE_PROJECT)

        symbol_id = resolver.make_symbol_id("myapp.utils", "Helper", "process")
        assert symbol_id == "myapp.utils.Helper.process"

        symbol_id = resolver.make_symbol_id("myapp.utils", "helper_func")
        assert symbol_id == "myapp.utils.helper_func"

    def test_resolve_absolute_import(self) -> None:
        """Test resolving absolute imports."""
        resolver = SymbolResolver(SAMPLE_PROJECT)

        result = resolver.resolve_import("myapp.utils", "os.path")
        assert result == "os.path"

    def test_resolve_relative_import_level_1(self) -> None:
        """Test resolving relative imports with level 1 (.)."""
        resolver = SymbolResolver(SAMPLE_PROJECT, "myapp")

        # from . import foo (in myapp.utils.helpers)
        result = resolver.resolve_import(
            "myapp.utils.helpers", "validators", is_relative=True, level=1
        )
        assert result == "myapp.utils.validators"

    def test_resolve_relative_import_level_2(self) -> None:
        """Test resolving relative imports with level 2 (..)."""
        resolver = SymbolResolver(SAMPLE_PROJECT, "myapp")

        # from .. import foo (in myapp.utils.helpers)
        result = resolver.resolve_import(
            "myapp.utils.helpers", "core", is_relative=True, level=2
        )
        assert result == "myapp.core"

    def test_resolve_relative_import_no_target(self) -> None:
        """Test resolving relative imports with no target (just dots)."""
        resolver = SymbolResolver(SAMPLE_PROJECT, "myapp")

        # from .. (in myapp.utils.helpers)
        result = resolver.resolve_import("myapp.utils.helpers", "", is_relative=True, level=2)
        assert result == "myapp"
