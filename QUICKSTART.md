# Quickstart

Author, inspect, run, and gate a governed mission — end to end, on your laptop, with no infrastructure.

## 1. Install

The SDK depends on the ReDevOps runtime (`agentic_os`). Until it is published, place this repo beside an
`agentic-os-src` checkout, or point `AGENTIC_OS_SRC` at one:

```bash
pip install -e .
# export AGENTIC_OS_SRC=/path/to/agentic-os-src     # if the runtime isn't a sibling checkout
```

## 2. Scaffold a mission

```bash
rdo mission init my_mission
# → wrote my_mission/mission.py  (a runnable fetch → process → [approval] publish starter)
```

## 3. Inspect it — no execution, no model calls

```bash
rdo mission validate my_mission/mission.py    # compiles? grants cover permissions? acyclic?
rdo mission explain  my_mission/mission.py    # the physical graph (deps, gates, side-effect/undo)
rdo mission profile  my_mission/mission.py    # EXPLAIN ANALYZE — topology + projected cost/latency/success
rdo mission simulate my_mission/mission.py    # dry-run projection vs budget
```

## 4. Run it on the local single-node profile

```bash
rdo mission run my_mission/mission.py             # parks on the human gate and reports it
rdo mission run my_mission/mission.py --approve   # drives the gate to completion
```

## 5. Prove it — bundle, replay, gate

```bash
rdo mission bundle my_mission/mission.py --out run.json   # portable, self-verifying case bundle
rdo mission replay my_mission/mission.py run.json         # rehydrate → same terminal state (tamper-detected)
rdo mission ci     my_mission/mission.py                  # promotion gate: feasibility·budget·run·regression·replay
```

## What you just used

You authored a mission and its capabilities through **one surface** (`redevops_mission`), held **one
artifact** (a versioned `MissionProgram`), and operated it entirely through `rdo mission` — never
importing a runtime internal. The `ci` gate is what a deploy would block on. Copy any of the missions
under [`examples/`](examples/) as a starting point, and drop
[`ci-templates/github-actions.yml`](ci-templates/github-actions.yml) into `.github/workflows/` to gate
every mission in your repo.
