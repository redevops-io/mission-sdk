"""`rdo mission init <name>` — scaffold a runnable starter mission.

Writes `<dir>/<name>/mission.py`: a three-step mission (fetch → process → [approval] publish) with its
capabilities, authored through the SDK surface. It validates and runs (`--approve`) out of the box, so a
new author edits a working mission rather than starting from a blank file.
"""
from __future__ import annotations

import os

_STARTER = '''"""{title} — a starter mission scaffolded by `rdo mission init`.

Edit the steps and capabilities below, then:
    rdo mission validate {name}/mission.py
    rdo mission run      {name}/mission.py --approve
    rdo mission ci       {name}/mission.py
"""
from __future__ import annotations

from redevops_mission import MissionProgram, Operator, capability, step, template


@template("{name}")
def {name}(mission_id):
    return [
        step("data_fetched", need="fetch the input the mission needs"),
        step("result_ready", need="process the input into a result", after=["data_fetched"]),
        step("result_published", need="publish the result",
             after=["result_ready"], constraints=["side effect — requires human approval"]),
    ]


OPERATORS = [
    Operator("{name}-worker", [
        capability("{name}.fetch", handler=lambda i: {{"data": "..."}},
                   provides=["data_fetched"], permissions=["{name}:read"]),
        capability("{name}.process", handler=lambda i: {{"result": "..."}},
                   provides=["result_ready"], permissions=["{name}:compute"]),
        capability("{name}.publish", handler=lambda i: {{"published": True}},
                   provides=["result_published"], side_effecting=True, approval_required=True,
                   undo="{name}.unpublish", permissions=["{name}:write"]),
    ]),
]

GRANTS = ["{name}:read", "{name}:compute", "{name}:write"]

PROGRAM = MissionProgram.from_template(
    "{name}", goal="TODO: describe what this mission achieves", grants=GRANTS,
)
'''


def init_mission(name: str, dest_dir: str = ".") -> str:
    """Create `<dest_dir>/<name>/mission.py` and return its path."""
    if not name.isidentifier():
        raise ValueError(f"mission name must be a valid Python identifier (got {name!r})")
    project = os.path.join(dest_dir, name)
    os.makedirs(project, exist_ok=True)
    path = os.path.join(project, "mission.py")
    if os.path.exists(path):
        raise FileExistsError(f"{path} already exists")
    title = name.replace("_", " ").title()
    with open(path, "w") as f:
        f.write(_STARTER.format(name=name, title=title))
    return path
