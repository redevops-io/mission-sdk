"""Resolve the runtime dependency (`agentic_os`).

In a released install this is a normal pinned dependency. For local development the SDK repo sits
beside the runtime checkout, so if `agentic_os` is not importable we add a sibling `agentic-os-src`
(or `$AGENTIC_OS_SRC`) to the path. This is the *only* place the SDK looks below its own boundary.
"""
from __future__ import annotations

import os
import sys


def ensure_runtime() -> None:
    try:
        import agentic_os  # noqa: F401
        return
    except ImportError:
        pass
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.environ.get("AGENTIC_OS_SRC"),
        os.path.join(repo_root, os.pardir, "agentic-os-src"),
    ]
    for c in candidates:
        if c and os.path.isdir(os.path.join(c, "agentic_os")):
            sys.path.insert(0, os.path.abspath(c))
            return
    raise ImportError(
        "the ReDevOps runtime (`agentic_os`) is not importable. Install `agentic-os`, or set "
        "AGENTIC_OS_SRC to a runtime checkout, or place this repo beside `agentic-os-src`."
    )
