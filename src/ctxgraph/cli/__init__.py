"""CLI entrypoints for ctxgraph."""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["build_parser", "main"]


def build_parser():
    """Build the CLI argument parser."""
    from .main import build_parser as _build_parser

    return _build_parser()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    from .main import main as _main

    return _main(argv)
