"""Utility functions for the sample project."""

import os
from pathlib import Path


def helper_function(x: int, y: int) -> int:
    """Add two numbers.

    Args:
        x: First number.
        y: Second number.

    Returns:
        Sum of x and y.
    """
    return x + y


async def async_helper(data: str) -> str:
    """Async helper function.

    Args:
        data: Input data.

    Returns:
        Processed data.
    """
    return data.upper()


class UtilityClass:
    """A utility class."""

    def __init__(self, name: str) -> None:
        """Initialize utility.

        Args:
            name: Name of the utility.
        """
        self.name = name

    def process(self, value: int) -> int:
        """Process a value.

        Args:
            value: Value to process.

        Returns:
            Processed value.
        """
        return value * 2

    @staticmethod
    def static_method() -> str:
        """A static method.

        Returns:
            A string.
        """
        return "static"
