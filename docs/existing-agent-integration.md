# Add ReDevOps to an existing agent without replacing it

The most common integration: you already have a working agent — a LangGraph graph, a LangChain chain, or a
plain function — and you want the ReDevOps Runtime's guarantees (a governed plan, execution, verification,
replay, explainability) **around** it, without rewriting the agent.

The answer is one idea: **wrap your existing call in a `capability` handler.** You do not port your agent
into the SDK; you register it as the thing that produces an outcome.

Runnable version: [`examples/01_existing_agent/main.py`](../examples/01_existing_agent/main.py).

## Before

```python
def answer(prompt: str) -> str:      # your agent — LangGraph .invoke(), a chain, a function, anything
    ...
    return result

result = answer("what is ReDevOps?")
```

## After

```python
from redevops_mission import (
    MissionProgram, Operator, capability, step, template, run_program, export_bundle, replay_bundle,
)

# 1. Describe the outcome your agent produces (and any dependencies between outcomes).
@template("agent_mission")
def agent_mission(mission_id):
    return [step("answer_ready", need="answer the user's prompt with the existing agent")]

# 2. Register your UNCHANGED agent as the capability that provides it.
OPERATORS = [Operator("my_app", [
    capability("app.answer",
               handler=lambda inputs: {"answer": answer(inputs.get("prompt", ""))},  # <- your call, wrapped
               provides=["answer_ready"]),
])]

# 3. Hold one artifact and run it as a governed, replayable mission.
PROGRAM = MissionProgram.from_template("agent_mission", goal="Answer the user", grants=[])
result = run_program(PROGRAM, OPERATORS)

# Inspect / replay — the runtime concerns you didn't have before.
bundle = export_bundle(PROGRAM, OPERATORS)
replay = replay_bundle(bundle, OPERATORS)   # reproduces the sealed run
```

## What stays yours, what the runtime owns

| Stays exactly as it is (yours) | The runtime adds (ReDevOps) |
|---|---|
| your agent / graph / chain / model calls | a compiled **plan** over your outcomes + dependencies |
| your business logic inside each handler | **execution** with dependency ordering + parallelism |
| your prompts, tools, providers | **verification** of the terminal state |
| your application UI | a portable, self-verifying **bundle** for **replay** |
| — | **explainability** (`explain`) and dry-run **simulation** (`simulate`) |

## Where each concern happens

- **Planning / ordering** — `MissionProgram.from_template(...)` compiles your `step`s (and their `after=`
  dependencies) into a physical graph. Independent steps run in parallel; `explain(PROGRAM, OPERATORS)`
  shows the compiled plan.
- **Execution** — `run_program(PROGRAM, OPERATORS)` invokes each capability handler in dependency order and
  returns a `RunResult` (`state`, `succeeded`, `outcome`, `nodes_succeeded`, `timeline`).
- **Verification** — `verify_bundle(bundle)` confirms the sealed run's integrity without re-running.
- **Replay / explain** — `export_bundle(...)` seals the run into a portable `CaseBundle`;
  `replay_bundle(bundle, OPERATORS)` rebuilds it and confirms it reproduces the terminal state
  (`replay.consistent`, `replay.recorded_state == replay.replayed_state`).

## Human approval and side effects

If a capability moves money, deletes data, or otherwise has an external effect, mark it and the runtime gates
it — a human approves before it runs, and it declares how to undo:

```python
capability("billing.charge", handler=charge_customer, provides=["charge_done"],
           side_effecting=True, approval_required=True, undo="billing.refund", permissions=["billing:write"])
```

Then `run_program(PROGRAM, OPERATORS, approve=True)` applies the pending approval; without it, the run parks
at the human gate. See [`examples/revenue_rescue/`](../examples/revenue_rescue/) for a full human-gated saga.

## What you should NOT do

- Do not port your agent's internals into the SDK — wrap the call, don't rewrite it.
- Do not import `agentic_os.*` — `redevops_mission` is the stable boundary.
- Do not treat ReDevOps as a replacement for LangGraph/LangChain — it runs beneath them. See
  [langgraph-integration.md](langgraph-integration.md) and [langchain-integration.md](langchain-integration.md).
