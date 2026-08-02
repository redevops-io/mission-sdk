"""The authoring surface — the declarative DSL a developer writes a mission and its capabilities in.

Everything here is re-exported from the runtime's internal SDK modules; the SDK's job is to make this
the *only* surface an author touches (no `agentic_os.mission.*` imports in user code). The one artifact
an author ends up holding is a `MissionProgram` (see `program.py`); `ExecutionIntent`/`IntentStep` are
the runtime's internal compile form and are deliberately not exported.
"""
from __future__ import annotations

from ._bootstrap import ensure_runtime

ensure_runtime()

# mission authoring: `@template` + `step(...)`
from agentic_os.mission.sdk import step, template  # noqa: E402,F401
# capability authoring: `capability(...)` builder + `Operator`
from agentic_os.mission.operator_sdk import Operator, capability  # noqa: E402,F401

__all__ = ["template", "step", "capability", "Operator"]


def build_intent(template_name: str, mission_id: str):
    """Internal: specialize a registered `@template` into the runtime's `ExecutionIntent` (kept internal)."""
    from agentic_os.mission.templates import TEMPLATES

    if template_name not in TEMPLATES:
        raise KeyError(
            f"no template named {template_name!r} is registered — declare it with @template({template_name!r})"
        )
    return TEMPLATES[template_name](mission_id)
