# redevops-mission — the Mission SDK

The curated developer boundary over the ReDevOps **Mission Runtime**. You author a mission and its
capabilities declaratively, hold **one artifact** — a versioned `MissionProgram` — and operate it
through this package and the `rdo mission` CLI, **without importing runtime internals**.

> Status: **M0** (design doc §10) — the package boundary + the two read-only verbs `validate` and
> `explain`, proven against the Revenue Rescue fixture. `run`/`replay`/`diff`/`verify`/`profile` and
> the local adapters land in M1–M2.

## Install (local development)

The SDK depends on the ReDevOps runtime (`agentic_os`). For local development, place this repo beside
an `agentic-os-src` checkout (or set `AGENTIC_OS_SRC`); a released install pins `agentic-os` instead.

```bash
pip install -e .        # exposes the `rdo` command
```

## Author a mission

A mission is a set of **steps** (each an `outcome` to produce, the `need` it satisfies, and its
dependencies) plus the **capabilities** that provide those outcomes. Everything is authored through
`redevops_mission` — see [`examples/revenue_rescue/mission.py`](examples/revenue_rescue/mission.py):

```python
from redevops_mission import MissionProgram, Operator, capability, step, template

@template("revenue_rescue")
def revenue_rescue(mission_id):
    return [
        step("dunning_attempted", need="chase the overdue invoice…",
             constraints=["money-moving — requires human approval"]),
        step("reply_drafted", need="proactively reach out…", after=["dunning_attempted"]),
        ...
    ]

OPERATORS = [Operator("agentic-billing", [
    capability("billing.dunning", handler=..., provides=["dunning_attempted"],
               side_effecting=True, approval_required=True, permissions=["billing:write"]),
]), ...]

PROGRAM = MissionProgram.from_template("revenue_rescue",
                                       goal="Recover a failed customer payment",
                                       grants=["billing:write", ...])
```

## Operate it

```bash
rdo mission validate examples/revenue_rescue/mission.py   # static + compile checks (no execution)
rdo mission explain  examples/revenue_rescue/mission.py   # render the compiled physical graph
```

`validate` runs the runtime's deterministic compile — every `need` must bind to a capability that
`provides` its outcome, the mission's `grants` must cover each capability's permissions (fail-closed),
and the graph must be acyclic. `explain` renders the lowered graph (dependencies, human gates,
side-effect/undo tags). Neither runs anything or calls a model.

## Design

The full design (the boundary, the `MissionProgram`-only public artifact, the `rdo mission` verbs
including `profile`, the adapter SPIs, and the M0→M3 plan) is in
`ReDevOps_Mission_SDK_and_DevOps_Design.md`.
