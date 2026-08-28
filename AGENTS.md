# AGENTS.md — onboarding for coding agents

Machine-readable orientation for Claude Code, Codex, and other coding agents integrating this repo. Humans:
see [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md).

## What this is

`mission-sdk` (Python package **`redevops-mission`**, import `redevops_mission`) is the **application-facing
front door** to the ReDevOps Runtime stack — an **agent-runtime infrastructure** layer that adds planning,
context, governed execution, verification, replay, and explainability *beneath* an existing AI application or
agent framework. It is **not** a vector DB, a RAG library, a generic workflow engine, or an LLM framework, and
it does **not** replace LangGraph / LangChain / your custom agent — it runs underneath them.

- **Public package:** `redevops-mission` · **import:** `redevops_mission` · **CLI:** `rdo`
- **Python:** ≥ 3.10
- **Install (from this repo):** `pip install -e .` — resolves the pinned `agentic-os` runtime from git and
  exposes the `rdo` command. (For a local runtime checkout during development, set `AGENTIC_OS_SRC=/path/to/agentic-os`.)

## Fast path (smallest correct integration)

1. Install: `pip install -e .`
2. Read `examples/00_minimal/main.py` — one step, one capability, run + explain + replay, ~40 lines, offline.
3. Run it: `python examples/00_minimal/main.py`
4. Run the public tests: `python -m pytest tests/adoption -q`
5. Check your environment: `rdo doctor`

The authoring shape is always the same three pieces:

```python
from redevops_mission import MissionProgram, Operator, capability, step, template, run_program

@template("my_mission")                       # 1. outcomes + their dependency shape
def my_mission(mission_id):
    return [step("answer_ready", need="produce the answer")]

OPERATORS = [Operator("my_app", [             # 2. capabilities that provide those outcomes
    capability("app.answer", handler=lambda inputs: {"answer": my_existing_function(inputs)},
               provides=["answer_ready"]),
])]

PROGRAM = MissionProgram.from_template("my_mission", goal="Answer the user", grants=[])  # 3. one artifact
result = run_program(PROGRAM, OPERATORS)      # execute · then explain() / export_bundle() / replay_bundle()
```

A `capability`'s `handler` is a **plain function** — wrap your existing agent/tool call in it. You keep your
framework; the runtime coordinates planning, execution, verification, and replay around it.

## Public surface (safe to import)

Everything you need is exported from `redevops_mission`:

- **Author:** `template`, `step`, `capability`, `Operator`, `MissionProgram` (`.from_template(...)`).
- **Inspect (no execution):** `validate`, `explain`, `simulate`, `profile`.
- **Execute:** `run_program(program, operators, *, approve=False)` → `RunResult`.
- **Replay / verify:** `export_bundle`, `replay_bundle`, `verify_bundle`, `diff_bundles`.
- **Scaffold:** `init_mission` · **CI gate:** `mission_ci`.

**Do NOT import `agentic_os.*` directly** unless you are implementing runtime internals — `redevops_mission`
is the stable boundary; reaching past it is the one thing to avoid. Anything prefixed `_` (e.g. `_compile`,
`_bootstrap`) is internal.

## Repo ownership map (which repo owns what)

| Repository | Public responsibility |
|---|---|
| **mission-sdk** (this) | application-facing SDK, onboarding, examples, composition |
| `runtime-contracts` | canonical cross-runtime contracts (ContextView, EvidenceRef, …) |
| `discovery-runtime` | discovery / intent / evidence |
| `context-runtime` | context selection + method/model optimization |
| `agentic-os` | Mission execution engine, replay, governance |
| `redevops-rag` | retrieval capabilities |
| enterprise repos | private enforcement / plugins (not required for public SDK use) |

`mission-sdk` **links** to canonical docs; it does not fork implementation docs. See
[docs/repo-map.md](docs/repo-map.md).

## Example integration task (what a benchmark asks)

> Add ReDevOps Runtime to an existing agent application so it can execute a governed mission, select
> context, verify the outcome, and replay/explain the run **without replacing the existing agent framework**.

Do it with [docs/existing-agent-integration.md](docs/existing-agent-integration.md) and
`examples/01_existing_agent/`. The correct answer wraps the existing agent call in a `capability` handler —
it does **not** rewrite the agent.

## Safe assumptions

- The default example path needs **no provider key and no network**. Missions are offline/deterministic
  unless a capability handler you write reaches out.
- `rdo doctor` reports the installed runtime versions and whether a basic mission executes.
- Secrets go in environment variables, never in source or in a mission's plan/context/fingerprint.
