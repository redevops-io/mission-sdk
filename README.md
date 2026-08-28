# Mission SDK — the ReDevOps Runtime front door

**The Mission SDK adds governed planning, execution, verification, and replay to your existing AI agents —
without replacing their framework.** Wrap a LangGraph, LangChain, or custom agent capability and run it as an
auditable, replayable mission. It is the application-facing front door to the ReDevOps Runtime, and integrates
with the stack's broader context/runtime capabilities (provider selection, optimization, discovery) as you
opt into them.

> **Works with your existing LangGraph, LangChain, custom agents, tools, models, and infrastructure.**
> Keep your agent framework. Stop rebuilding the production runtime around every app.

![python](https://img.shields.io/badge/python-3.10%2B-blue)
![package](https://img.shields.io/badge/package-redevops--mission-informational)
![license](https://img.shields.io/badge/license-Apache--2.0-green)
![status](https://img.shields.io/badge/status-alpha%20(M3)-orange)

**[Quickstart](QUICKSTART.md) · [Architecture](ARCHITECTURE.md) · [Examples](examples/) · [For coding agents](AGENTS.md)**

Category: **Agent Automation / Agent Runtime Infrastructure** — *not* a vector database, RAG library, generic
workflow engine, or LLM framework.

## Install

```bash
git clone https://github.com/redevops-io/mission-sdk
cd mission-sdk
pip install -e .          # resolves the pinned agentic-os runtime; exposes the `rdo` command
rdo doctor               # versions + a live minimal-mission run — confirms the environment
```

> Not yet on PyPI. Once published, the one-liner will be `pip install redevops-mission`.

Optional adoption extras: `pip install -e ".[langgraph]"`, `".[langchain]"`, `".[telemetry]"`, `".[full]"`.
The default install needs **no provider key and no network** to run the minimal example below.

## Minimal working example

```python
from redevops_mission import (
    MissionProgram, Operator, capability, step, template, run_program, explain, export_bundle, replay_bundle,
)

@template("hello_mission")                        # 1. outcomes + their dependency shape
def hello_mission(mission_id):
    return [step("greeting_ready", need="produce a greeting for the user")]

OPERATORS = [Operator("greeter", [                # 2. capabilities that provide them (wrap YOUR logic)
    capability("greet.hello", handler=lambda inputs: {"greeting": "hello from the runtime"},
               provides=["greeting_ready"]),
])]

PROGRAM = MissionProgram.from_template("hello_mission", goal="Greet the user", grants=[])  # 3. one artifact

result = run_program(PROGRAM, OPERATORS)          # execute
exp    = explain(PROGRAM, OPERATORS)              # why this plan
replay = replay_bundle(export_bundle(PROGRAM, OPERATORS), OPERATORS)   # reproduce the sealed run
print(result.succeeded, replay.consistent)        # -> True True
```

Runnable, offline, and CI-tested at [`examples/00_minimal/main.py`](examples/00_minimal/main.py):

```bash
python examples/00_minimal/main.py
# run     : state=succeeded succeeded=True nodes=1
# explain : goal='Greet the user', 1 node(s), first=greet.hello -> greeting_ready
# replay  : recorded=succeeded replayed=succeeded consistent=True integrity_ok=True
# OK — mission executed, explained, replayed, and verified.
```

## What ReDevOps is (and is not)

| ReDevOps Runtime | Does **not** replace |
|---|---|
| runtime layer beneath applications | LangGraph |
| context / evidence planning | LangChain |
| governed mission execution | your business logic |
| verification / replay | your model provider |
| runtime telemetry / governance seams | your infrastructure |
| provider / runtime optimization | your application UI |

It runs **beneath** your agent. The single most useful guide is
[**Add ReDevOps to an existing agent without replacing it**](docs/existing-agent-integration.md) — the
correct integration wraps your existing call in a `capability`; it does not rewrite your agent.

## What the public tests prove

- installation works from a clean environment;
- the minimal mission executes offline and deterministically;
- an existing agent can be wrapped without a rewrite;
- **replay reproduces the sealed plan** and terminal state;
- a case bundle **verifies its own integrity** without re-running;
- the security / telemetry plane is opt-in, not required for basic use.

The full map is [docs/public-test-matrix.md](docs/public-test-matrix.md). Run it: `python -m pytest -q` (or a
guarantee group, e.g. `python -m pytest tests/adoption -q`).

## Operate a mission (`rdo` CLI)

```bash
rdo doctor                                        # environment + live minimal-mission check
rdo mission validate examples/revenue_rescue/mission.py   # static + compile checks (no execution)
rdo mission explain  examples/revenue_rescue/mission.py   # the compiled physical graph
rdo mission simulate examples/revenue_rescue/mission.py   # dry-run cost/latency/approvals/success
rdo mission run      examples/revenue_rescue/mission.py --approve   # execute on the local profile
rdo mission bundle   examples/revenue_rescue/mission.py --out run.json   # seal a replayable bundle
rdo mission replay   examples/revenue_rescue/mission.py run.json         # reproduce it
```

Full verb list and the M3 status: [QUICKSTART.md](QUICKSTART.md).

## Public AGPL stack vs enterprise extensions

The public AGPL stack is the **open runtime contract and reference implementation** — canonical contracts,
public runtime interfaces, and context/planning/execution/replay capabilities as actually shipped, with the
public examples and tests. It is not a crippled demo.

**Enterprise extensions** (separate, private repos) add production security enforcement, telemetry bridges,
deployment adapters, secret-store plugins, and long-haul storage. They are **optional** and never required
for public SDK use.

## Repository role & map

`mission-sdk` is the public front door — onboarding, composition, examples — and **links** to the canonical
repos rather than forking their implementations. See [docs/repo-map.md](docs/repo-map.md) for which repo owns
each subsystem (`runtime-contracts`, `context-runtime`, `discovery-runtime`, `agentic-os`, `redevops-rag`),
[COMPATIBILITY.md](COMPATIBILITY.md) for pinned versions, and [PARITY.md](PARITY.md) for the SDK↔runtime
contract check.

## Developing against a local runtime

`pip install -e .` resolves the pinned `agentic-os` from git. For development against a **local** runtime
checkout, set `AGENTIC_OS_SRC=/path/to/agentic-os` — a loud, opt-in override (unset ⇒ a clear ImportError, so
the SDK is never silently satisfied by an unknown checkout). See [ARCHITECTURE.md](ARCHITECTURE.md) and
[CONTRIBUTING](CONTRIBUTING.md) if present.
