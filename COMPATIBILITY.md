# Compatibility matrix

The version of `redevops-mission` (mission-sdk) that you install pins the ReDevOps Runtime it drives. This
page is the human-readable matrix; `rdo doctor` reports what is **actually installed** and whether it works.

| Component | This release | Notes |
|---|---|---|
| **mission-sdk** (`redevops-mission`) | `0.3.8` | this repo — the public SDK boundary |
| Python | `>= 3.11` | `requires-python` in `pyproject.toml` |
| `agentic-os` | pinned at tag `v0.3.39` (`pyproject.toml`; latest agentic-os tag at 2026-10-17) | hard dependency — the Mission execution/replay/governance engine, resolved from git by `pip install` |
| `runtime-contracts` | `>= 0.3` (not enforced by this SDK's `pyproject.toml`) | canonical contracts (pulled transitively where used) |
| `context-runtime` | not enforced | context/optimization capabilities (optional at runtime). Its `__version__` is `0.1.0`; tags `v0.1.0`, `v0.2.0`, `v0.3.0` and `wN` exist, so a numeric minimum is ambiguous. |
| `discovery-runtime` | `v0.1.x` line | discovery/intent/evidence (optional at runtime). Its real line is `v0.1.x`; tags `v0.3.0` and `v0.4.0` are superseded strays (see that repo's README), so do not pin by numeric minimum. |
| `redevops-rag` | not enforced | retrieval capabilities (optional at runtime) |

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
mission-sdk        0.3.8                        OK
python             3.12.14                      OK
agentic-os         0.3.39                       OK
minimal mission    runs                         OK
```

## Optional extras

```bash
# redevops-mission is not on PyPI; install extras from the git tag (or `pip install -e ".[langgraph]"` in a clone)
pip install "redevops-mission[langgraph] @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.8"   # LangGraph deps
pip install "redevops-mission[langchain] @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.8"   # LangChain deps
pip install "redevops-mission[telemetry] @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.8"   # telemetry bridges
pip install "redevops-mission[full] @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.8"        # everything above
```

The default install needs **no provider key and no extra** to run
`examples/00_minimal/main.py`.

## Release discipline

Each `mission-sdk` release: pins compatible runtime versions · runs the full public example suite ·
runs the clean-install test · validates all docs commands and links · runs the tenant-isolation regression ·
publishes a changelog · updates this matrix · tags · and verifies the install. (No package index is used: nothing is published to PyPI.)
See the plan's §28.
