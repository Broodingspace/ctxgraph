"""Tests for sample project models used in impact-report demos."""

from sample_project.models import User


def test_user_display_name_includes_id() -> None:
    """The display name should include the user ID and name."""
    user = User(7, "Ada")
    assert user.get_display_name() == "User<7>: Ada"
