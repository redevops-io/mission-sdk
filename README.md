# redevops-mission — the Mission SDK

The curated developer boundary over the ReDevOps **Mission Runtime**. You author a mission and its
capabilities declaratively, hold **one artifact** — a versioned `MissionProgram` — and operate it
through this package and the `rdo mission` CLI, **without importing runtime internals**.

> Status: **M2** (design doc §10). Verbs: `validate` · `explain` · `profile` · `simulate` · `run` ·
> `bundle` · `replay` · `diff` · `verify`. Proven against three dogfood fixtures — Revenue Rescue (a
> human-gated saga), DataOpsBench S21 (a parallel-extract → merge → verify mission), and Deploy Release
> (a net-new gated pipeline). A run exports a portable, self-verifying **case bundle** that `replay`
> rehydrates to the same terminal state.

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
rdo mission profile  examples/revenue_rescue/mission.py   # EXPLAIN ANALYZE — topology + projections
rdo mission simulate examples/revenue_rescue/mission.py   # dry-run cost/latency/approvals/success
rdo mission run      examples/revenue_rescue/mission.py --approve   # execute on the local profile
```

- **`validate`** runs the runtime's deterministic compile — every `need` must bind to a capability that
  `provides` its outcome, the mission's `grants` must cover each capability's permissions (fail-closed),
  and the graph must be acyclic.
- **`explain`** renders the lowered graph (dependencies, human gates, side-effect/undo tags).
- **`profile`** is EXPLAIN ANALYZE: topology (critical-path depth, parallelism, merge points, gate/
  side-effect/undo coverage) plus projected cost/latency/success — all static, no execution.
- **`simulate`** projects cost/success/latency/approvals against the mission budget.
- **`run`** executes on the **local single-node profile** (in-memory, zero infra). It parks on human
  gates and reports them; `--approve` drives them to completion; `--ledger PATH` persists the event log.
- **`bundle`** runs the mission and exports a portable, self-verifying **case bundle** (events + outcome
  + content digest) — `rdo mission bundle <target> --out run.json`.
- **`replay`** rebuilds a fresh runtime from a bundle's events and confirms it reaches the **same
  terminal state** (the event log is a faithful, replayable record; tampering is detected) —
  `rdo mission replay <target> run.json`.
- **`diff`** reports the structural differences between two bundles — `rdo mission diff a.json b.json`.
- **`verify`** runs the mission and reports what the runtime recorded: terminal success, ledger
  integrity, verification stages, and nodes succeeded.

`validate`/`explain`/`profile`/`simulate` never run anything or call a model. The three dogfood fixtures
live under [`examples/`](examples/): `revenue_rescue` (branching saga), `dataops_reconcile` (DataOpsBench
S21 merge/verify), and `deploy_release` (a net-new gated pipeline).

## Design

The full design (the boundary, the `MissionProgram`-only public artifact, the `rdo mission` verbs
including `profile`, the adapter SPIs, and the M0→M3 plan) is in
`ReDevOps_Mission_SDK_and_DevOps_Design.md`.
