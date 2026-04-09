"""Tests for AST parser module."""

from pathlib import Path

import pytest

from ctxgraph.parser import ASTParser, parse_python_file

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


class TestASTParser:
    """Test AST parsing functionality."""

    def test_parse_utils_file(self) -> None:
        """Test parsing utils.py."""
        parser = ASTParser()
        result = parser.parse_file(SAMPLE_PROJECT / "utils.py")

        assert len(result.errors) == 0
        assert result.module_docstring is not None

        # Check imports
        assert len(result.imports) >= 2
        import_modules = [imp.module for imp in result.imports]
        assert "os" in import_modules
        assert "pathlib" in import_modules

        # Check functions
        func_names = [f.name for f in result.functions]
        assert "helper_function" in func_names
        assert "async_helper" in func_names

        # Check async function
        async_funcs = [f for f in result.functions if f.is_async]
        assert len(async_funcs) == 1
        assert async_funcs[0].name == "async_helper"

        # Check classes
        assert len(result.classes) == 1
        assert result.classes[0].name == "UtilityClass"

        # Check methods
        util_class = result.classes[0]
        method_names = [m.name for m in util_class.methods]
        assert "__init__" in method_names
        assert "process" in method_names
        assert "static_method" in method_names

    def test_parse_models_file(self) -> None:
        """Test parsing models.py."""
        parser = ASTParser()
        result = parser.parse_file(SAMPLE_PROJECT / "models.py")

        assert len(result.errors) == 0

        # Check imports
        imports = result.imports
        assert len(imports) > 0

        # Check relative import
        relative_imports = [imp for imp in imports if imp.is_relative]
        assert len(relative_imports) == 1
        assert relative_imports[0].level == 1

        # Check classes
        class_names = [c.name for c in result.classes]
        assert "BaseModel" in class_names
        assert "User" in class_names
        assert "Product" in class_names

        # Check inheritance
        user_class = next(c for c in result.classes if c.name == "User")
        assert "BaseModel" in user_class.bases

        product_class = next(c for c in result.classes if c.name == "Product")
        assert "BaseModel" in product_class.bases

    def test_parse_function_details(self) -> None:
        """Test extracting function details."""
        parser = ASTParser()
        result = parser.parse_file(SAMPLE_PROJECT / "utils.py")

        helper_func = next(f for f in result.functions if f.name == "helper_function")

        # Check location
        assert helper_func.lineno > 0
        assert helper_func.end_lineno >= helper_func.lineno

        # Check docstring
        assert helper_func.docstring is not None
        assert "Add two numbers" in helper_func.docstring

        # Check arguments
        assert "x" in helper_func.args
        assert "y" in helper_func.args

    def test_parse_class_details(self) -> None:
        """Test extracting class details."""
        parser = ASTParser()
        result = parser.parse_file(SAMPLE_PROJECT / "utils.py")

        util_class = result.classes[0]

        # Check docstring
        assert util_class.docstring is not None

        # Check location
        assert util_class.lineno > 0
        assert util_class.end_lineno >= util_class.lineno

        # Check methods have metadata
        process_method = next(m for m in util_class.methods if m.name == "process")
        assert process_method.docstring is not None
        assert "value" in process_method.args

    def test_parse_decorators(self) -> None:
        """Test extracting decorators."""
        parser = ASTParser()
        result = parser.parse_file(SAMPLE_PROJECT / "utils.py")

        util_class = result.classes[0]
        static_method = next(m for m in util_class.methods if m.name == "static_method")

        assert "staticmethod" in static_method.decorators

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing nonexistent file."""
        parser = ASTParser()
        result = parser.parse_file("/nonexistent/file.py")

        assert len(result.errors) > 0
        assert "Failed to read file" in result.errors[0]

    def test_convenience_function(self) -> None:
        """Test convenience function."""
        result = parse_python_file(SAMPLE_PROJECT / "utils.py")

        assert len(result.errors) == 0
        assert len(result.functions) > 0
        assert len(result.classes) > 0
