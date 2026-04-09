"""Tests for file discovery module."""

from pathlib import Path

import pytest

from ctxgraph.parser import FileDiscovery, discover_python_files

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


class TestFileDiscovery:
    """Test file discovery functionality."""

    def test_discover_sample_project(self) -> None:
        """Test discovering files in sample project."""
        discovery = FileDiscovery(SAMPLE_PROJECT)
        files = discovery.discover()

        assert len(files) > 0
        assert all(f.suffix == ".py" for f in files)
        assert all(f.is_absolute() for f in files)

    def test_exclude_directories(self) -> None:
        """Test excluding specific directories."""
        # Test excluding __pycache__ (which is in defaults)
        discovery = FileDiscovery(SAMPLE_PROJECT)
        files = discovery.discover()

        # Should not include any files from __pycache__
        for file_path in files:
            assert "__pycache__" not in file_path.parts

    def test_discover_single_file(self) -> None:
        """Test discovering a single file."""
        single_file = SAMPLE_PROJECT / "utils.py"
        discovery = FileDiscovery(single_file)
        files = discovery.discover()

        assert len(files) == 1
        assert files[0] == single_file

    def test_discover_nonexistent_path(self) -> None:
        """Test discovering in nonexistent path."""
        discovery = FileDiscovery("/nonexistent/path")
        files = discovery.discover()

        assert len(files) == 0

    def test_convenience_function(self) -> None:
        """Test convenience function."""
        files = discover_python_files(SAMPLE_PROJECT)

        assert len(files) > 0
        assert all(f.suffix == ".py" for f in files)
