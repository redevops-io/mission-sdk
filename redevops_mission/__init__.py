"""redevops_mission — the Mission SDK.

The curated public boundary over the ReDevOps Mission Runtime. A developer authors a mission and its
capabilities with the DSL, holds one artifact (`MissionProgram`), and operates it through this package
and the `rdo mission` CLI — never importing `agentic_os.mission.*` directly.

M0 surface: authoring (`template`, `step`, `capability`, `Operator`), the `MissionProgram` artifact,
and the two read-only verbs `validate` and `explain`.
"""
from __future__ import annotations

from .api import Explanation, ValidateReport, explain, validate
from .authoring import Operator, capability, step, template
from .program import MissionProgram, MissionStep

__version__ = "0.1.0a0"

__all__ = [
    "template", "step", "capability", "Operator",
    "MissionProgram", "MissionStep",
    "validate", "explain", "ValidateReport", "Explanation",
]
