"""Resolve the runtime dependency (`agentic_os`).

In a released install this is the pinned `agentic-os` dependency (see `pyproject.toml` / `PARITY.md`) and
this module is a no-op. For local development against a runtime checkout, set `AGENTIC_OS_SRC` — that is
the **only** override, and it warns loudly, so the SDK is never silently satisfied by an unknown checkout.
"""
from __future__ import annotations

import os
import sys
import warnings


def ensure_runtime() -> None:
    try:
        import agentic_os  # noqa: F401
        return
    except ImportError:
        pass

    src = os.environ.get("AGENTIC_OS_SRC")
    if src and os.path.isdir(os.path.join(src, "agentic_os")):
        sys.path.insert(0, os.path.abspath(src))
        warnings.warn(
            f"redevops_mission: using a DEV runtime checkout from AGENTIC_OS_SRC={src}, "
            "not the pinned `agentic-os` dependency.",
            RuntimeWarning, stacklevel=2,
        )
        return

    raise ImportError(
        "the ReDevOps runtime (`agentic_os`) is not importable. Install the SDK's pinned dependency "
        "(`pip install -e .` resolves `agentic-os`), or set AGENTIC_OS_SRC to a runtime checkout for "
        "development."
    )
