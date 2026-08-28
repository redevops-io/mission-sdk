# LangChain integration

Same principle as [LangGraph](langgraph-integration.md) and the
[existing-agent guide](existing-agent-integration.md): ReDevOps runs **beneath** your chain. Keep the chain;
wrap its `.invoke()` in a mission `capability` to get a governed plan, verification, and replay.

```python
chain = build_your_chain()                          # your existing LangChain chain, unchanged

from redevops_mission import MissionProgram, Operator, capability, step, template, run_program

@template("chain_mission")
def chain_mission(mission_id):
    return [step("answer_ready", need="run the LangChain chain to answer the prompt")]

OPERATORS = [Operator("my_chain_app", [
    capability("chain.invoke",
               handler=lambda inputs: {"answer": chain.invoke(inputs.get("prompt", ""))},
               provides=["answer_ready"]),
])]

PROGRAM = MissionProgram.from_template("chain_mission", goal="Answer via the chain", grants=[])
result = run_program(PROGRAM, OPERATORS)
```

**Division of labour:** LangChain owns prompt/tool/model composition inside the handler; ReDevOps owns the
cross-capability plan, approval gates, verification, and replay around it. Multi-stage pipelines become
multiple `step`s + `capability`s so each is individually governed and replayable.

`langchain` is an optional extra: `pip install "redevops-mission[langchain]"`.
