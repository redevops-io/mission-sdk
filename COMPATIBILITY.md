# Compatibility matrix

The version of `redevops-mission` (mission-sdk) that you install pins the ReDevOps Runtime it drives. This
page is the human-readable matrix; `rdo doctor` reports what is **actually installed** and whether it works.

| Component | This release | Notes |
|---|---|---|
| **mission-sdk** (`redevops-mission`) | `0.2.0a0` | this repo — the public SDK boundary |
| Python | `>= 3.10` | |
| `agentic-os` | pinned at commit `63c0b255` | hard dependency — the Mission execution/replay/governance engine, resolved from git by `pip install` |
| `runtime-contracts` | `>= 0.3` | canonical contracts (pulled transitively where used) |
| `context-runtime` | `>= 0.2` | context/optimization capabilities (optional at runtime) |
| `discovery-runtime` | `>= 0.3` | discovery/intent/evidence (optional at runtime) |
| `redevops-rag` | `>= 0.2` | retrieval capabilities (optional at runtime) |

Only `agentic-os` is a **hard** dependency of the default install; the sibling runtimes are pulled in when a
capability actually uses them. The pins move together each `mission-sdk` release (see [Release
discipline](#release-discipline)).

## Check your install

```bash
rdo doctor
```

Reports the installed component versions, whether the runtime imports, and whether a basic mission executes
— the fastest way to confirm an environment is benchmark-ready. Example output:

```text
mission-sdk        0.2.0a0   OK
python             3.12.x    OK
agentic-os         <ver>     OK
runtime available  yes       OK
minimal mission    runs      OK
```

## Optional extras

From a clone (the package is not yet on PyPI — see the [README](README.md#install)):

```bash
pip install -e ".[langgraph]"   # LangGraph integration deps
pip install -e ".[langchain]"   # LangChain integration deps
pip install -e ".[telemetry]"   # telemetry bridges
pip install -e ".[full]"        # everything above
```

The default `pip install -e .` needs **no provider key and no extra** to run
`examples/00_minimal/main.py`.

## Release discipline

Each `mission-sdk` release: pins compatible runtime versions · runs the full public example suite ·
runs the clean-install test · validates all docs commands and links · runs the tenant-isolation regression ·
publishes a changelog · updates this matrix · tags · and verifies install from the published package index.
See the plan's §28.
