# LangGraph integration

ReDevOps runs **beneath** your LangGraph graph — it does not replace graph orchestration. Keep your graph;
register its `.invoke()` as a mission `capability` so the run gets a governed plan, verification, and replay.

Read [existing-agent-integration.md](existing-agent-integration.md) first — the pattern is identical; the
only difference is what the handler calls.

```python
from langgraph.graph import StateGraph            # your existing graph, unchanged
graph = build_your_graph()                         # -> a compiled graph with .invoke()

from redevops_mission import MissionProgram, Operator, capability, step, template, run_program

@template("graph_mission")
def graph_mission(mission_id):
    return [step("answer_ready", need="run the LangGraph graph to answer the prompt")]

OPERATORS = [Operator("my_graph_app", [
    capability("graph.invoke",
               handler=lambda inputs: {"answer": graph.invoke({"prompt": inputs.get("prompt", "")})},
               provides=["answer_ready"]),
])]

PROGRAM = MissionProgram.from_template("graph_mission", goal="Answer via the graph", grants=[])
result = run_program(PROGRAM, OPERATORS)   # then export_bundle()/replay_bundle() as usual
```

**Division of labour:** LangGraph owns the node/edge orchestration *inside* a capability; ReDevOps owns the
cross-capability plan, human-approval gates, verification, and replay *around* it. If your workflow is a
single graph, that's one capability; if it's several stages you want individually governed/replayable, make
each stage a `step` + `capability` and let the runtime order them.

`langgraph` is an optional extra: `pip install "redevops-mission[langgraph]"`.
