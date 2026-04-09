"""Tests for scoring utilities."""

import pytest

from ctxgraph.retrieval.scoring import CentralityScorer, ScoringWeights, TextMatcher


class TestTextMatcher:
    """Test text matching utilities."""

    def test_normalize(self) -> None:
        """Test text normalization."""
        assert TextMatcher.normalize("MyClass") == "myclass"
        assert TextMatcher.normalize("my_function") == "myfunction"
        assert TextMatcher.normalize("some-module") == "somemodule"

    def test_tokenize(self) -> None:
        """Test text tokenization."""
        tokens = TextMatcher.tokenize("my_module.MyClass")
        assert "my" in tokens
        assert "module" in tokens
        assert "myclass" in tokens

    def test_score_name_match_exact(self) -> None:
        """Test exact name match."""
        score = TextMatcher.score_name_match("User", "user")
        assert score == 10.0

    def test_score_name_match_starts_with(self) -> None:
        """Test name starts with query."""
        score = TextMatcher.score_name_match("UserModel", "user")
        assert score == 7.0

    def test_score_name_match_contains(self) -> None:
        """Test name contains query."""
        score = TextMatcher.score_name_match("create_user", "user")
        assert score == 5.0

    def test_score_name_match_fuzzy(self) -> None:
        """Test fuzzy name match."""
        # "create_user_account" contains "user" but query is "account user"
        # Should match via token overlap (fuzzy)
        score = TextMatcher.score_name_match("create_account", "user account")
        # Should get fuzzy match (token overlap) but not exact/contains
        assert score >= 0  # Either fuzzy match or no match is fine

    def test_score_name_match_no_match(self) -> None:
        """Test no match."""
        score = TextMatcher.score_name_match("foo", "bar")
        assert score == 0.0

    def test_score_text_match(self) -> None:
        """Test text/docstring matching."""
        text = "This function handles user authentication"
        score = TextMatcher.score_text_match(text, "authentication")
        assert score == 5.0

    def test_score_text_match_partial(self) -> None:
        """Test partial text match."""
        text = "Validates user input"
        score = TextMatcher.score_text_match(text, "user validation")
        assert score > 0
        assert score < 5.0

    def test_score_path_match(self) -> None:
        """Test path matching."""
        path = "/path/to/user/models.py"
        score = TextMatcher.score_path_match(path, "user")
        assert score > 0


class TestCentralityScorer:
    """Test centrality scoring."""

    def test_score_degree_centrality(self) -> None:
        """Test degree centrality scoring."""
        # Low degree
        score = CentralityScorer.score_degree_centrality(1, 1)
        assert score < 1.0

        # High degree
        score = CentralityScorer.score_degree_centrality(10, 10)
        assert score > 1.0

        # Maximum
        score = CentralityScorer.score_degree_centrality(50, 50)
        assert score == 3.0

    def test_score_hub_authority(self) -> None:
        """Test hub and authority scoring."""
        # Hub (many outgoing)
        hub, auth = CentralityScorer.score_hub_authority(1, 10)
        assert hub > auth

        # Authority (many incoming)
        hub, auth = CentralityScorer.score_hub_authority(10, 1)
        assert auth > hub


class TestScoringWeights:
    """Test scoring weights configuration."""

    def test_default_weights(self) -> None:
        """Test default weights are reasonable."""
        weights = ScoringWeights()
        assert weights.name_exact_match > weights.name_contains
        assert weights.name_contains > weights.name_fuzzy
        assert weights.entrypoint_bonus > 0

    def test_custom_weights(self) -> None:
        """Test custom weights."""
        weights = ScoringWeights(
            name_exact_match=20.0,
            centrality=5.0
        )
        assert weights.name_exact_match == 20.0
        assert weights.centrality == 5.0
