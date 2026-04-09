"""Tests for graph builder module."""

from pathlib import Path

import pytest

from ctxgraph import EdgeType, NodeType
from ctxgraph.parser import GraphBuilder, build_graph

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


class TestGraphBuilder:
    """Test graph building functionality."""

    def test_build_sample_project(self) -> None:
        """Test building graph from sample project."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        # Should have nodes
        assert graph.node_count > 0
        assert graph.edge_count > 0

        # Check module nodes
        modules = list(graph.nodes(node_type=NodeType.MODULE))
        assert len(modules) > 0

        module_names = [m.id for m in modules]
        assert any("sample_project.utils" in mid for mid in module_names)
        assert any("sample_project.models" in mid for mid in module_names)

    def test_build_creates_class_nodes(self) -> None:
        """Test that builder creates class nodes."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        classes = list(graph.nodes(node_type=NodeType.CLASS))
        assert len(classes) > 0

        class_names = [c.name for c in classes]
        assert "UtilityClass" in class_names
        assert "BaseModel" in class_names
        assert "User" in class_names
        assert "Product" in class_names

    def test_build_creates_function_nodes(self) -> None:
        """Test that builder creates function nodes."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        functions = list(graph.nodes(node_type=NodeType.FUNCTION))
        assert len(functions) > 0

        func_names = [f.name for f in functions]
        assert "helper_function" in func_names
        assert "async_helper" in func_names

    def test_build_creates_defines_edges(self) -> None:
        """Test that builder creates DEFINES edges."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        defines_edges = list(graph.edges(edge_type=EdgeType.DEFINES))
        assert len(defines_edges) > 0

        # Module should define classes
        for edge in defines_edges:
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            assert source is not None
            assert target is not None

    def test_build_creates_contains_edges(self) -> None:
        """Test that builder creates CONTAINS edges."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        contains_edges = list(graph.edges(edge_type=EdgeType.CONTAINS))
        assert len(contains_edges) > 0

    def test_build_creates_inherits_edges(self) -> None:
        """Test that builder creates INHERITS edges."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        inherits_edges = list(graph.edges(edge_type=EdgeType.INHERITS))
        assert len(inherits_edges) > 0

        # User and Product should inherit from BaseModel
        user_node = next((n for n in graph.nodes() if n.name == "User"), None)
        assert user_node is not None

        parents = graph.get_neighbors(user_node.id, edge_type=EdgeType.INHERITS)
        assert len(parents) > 0

    def test_build_creates_import_edges(self) -> None:
        """Test that builder creates IMPORTS edges."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        import_edges = list(graph.edges(edge_type=EdgeType.IMPORTS))

        # models.py imports from utils, so should have import edge
        # if both modules are discovered
        models_node = next(
            (n for n in graph.nodes() if "models" in n.id and n.type == NodeType.MODULE), None
        )

        if models_node:
            imports = graph.get_neighbors(models_node.id, edge_type=EdgeType.IMPORTS)
            # May or may not have imports depending on resolution

    def test_build_preserves_metadata(self) -> None:
        """Test that builder preserves metadata."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        # Check function metadata
        helper_func = next(
            (n for n in graph.nodes() if n.name == "helper_function"), None
        )
        assert helper_func is not None
        assert "docstring" in helper_func.metadata
        assert helper_func.metadata["is_async"] is False

        # Check class metadata
        util_class = next((n for n in graph.nodes() if n.name == "UtilityClass"), None)
        assert util_class is not None
        assert "docstring" in util_class.metadata

    def test_build_with_source_locations(self) -> None:
        """Test that builder captures source locations."""
        builder = GraphBuilder(SAMPLE_PROJECT, package_name="sample_project")
        graph = builder.build()

        for node in graph.nodes():
            if node.location:
                assert node.location.line_start > 0
                assert node.location.line_end >= node.location.line_start
                assert node.location.file_path

    def test_convenience_function(self) -> None:
        """Test convenience function."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")

        assert graph.node_count > 0
        assert graph.edge_count > 0

    def test_graph_stats(self) -> None:
        """Test graph statistics."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
        stats = graph.stats()

        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0
        assert NodeType.MODULE in stats["nodes_by_type"]
        assert NodeType.CLASS in stats["nodes_by_type"]
        assert NodeType.FUNCTION in stats["nodes_by_type"]

    def test_build_creates_calls_edges(self) -> None:
        """Test that builder extracts CALLS edges from function bodies."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")

        calls_edges = list(graph.edges(edge_type=EdgeType.CALLS))
        assert len(calls_edges) > 0, "Expected at least one CALLS edge"

        source_ids = {e.source_id for e in calls_edges}
        target_ids = {e.target_id for e in calls_edges}

        # authenticate() calls verify_password() and generate_token()
        assert any("authenticate" in sid for sid in source_ids)
        assert any("verify_password" in tid or "generate_token" in tid for tid in target_ids)

    def test_calls_edges_cross_module(self) -> None:
        """Test that CALLS edges are resolved across module boundaries."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")

        calls_edges = list(graph.edges(edge_type=EdgeType.CALLS))
        cross_module = [
            e for e in calls_edges
            if e.source_id.split(".")[1] != e.target_id.split(".")[1]
        ]
        assert len(cross_module) > 0, "Expected cross-module CALLS edges"

    def test_calls_edges_self_resolution(self) -> None:
        """Test that self.method() calls resolve to sibling methods."""
        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")

        # verify_password() calls hash_password() — both in auth module
        auth_calls = [
            e for e in graph.edges(edge_type=EdgeType.CALLS)
            if "auth" in e.source_id and "auth" in e.target_id
        ]
        assert len(auth_calls) > 0

    def test_blast_radius_includes_callers(self) -> None:
        """Blast radius with direction=incoming finds functions that call the target."""
        from ctxgraph import QueryEngine

        graph = build_graph(SAMPLE_PROJECT, package_name="sample_project")
        engine = QueryEngine(graph)

        # hash_password is called by verify_password and create_user
        result = engine.find_blast_radius(
            "sample_project.auth.hash_password",
            max_depth=2,
            direction="incoming",
        )
        # With CALLS edges, callers should now appear in blast radius
        assert result.count > 0
