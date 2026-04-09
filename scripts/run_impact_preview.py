"""Run a local preview of the ctxgraph PR impact report."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run the GitHub Action helper script with local-preview defaults."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", default=".", help="Repository root to analyze.")
    parser.add_argument("--base-ref", default="main", help="Base git ref or SHA.")
    parser.add_argument("--head-ref", default="HEAD", help="Head git ref or SHA.")
    parser.add_argument(
        "--markdown-out",
        default=".ctxgraph/impact-report.md",
        help="Path to write the markdown report preview.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_path).resolve()
    script_path = repo_root / "scripts" / "github_action.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--repo-path",
        str(repo_root),
        "--base-ref",
        args.base_ref,
        "--head-ref",
        args.head_ref,
        "--comment-mode",
        "none",
        "--markdown-out",
        args.markdown_out,
    ]
    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
