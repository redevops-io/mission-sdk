# Mission SDK (`redevops-mission`)

**What it does.** A small Python SDK for authoring, validating, explaining, running, sealing and replaying a
governed `MissionProgram`: a plan whose side-effecting steps are gated on explicit approval and whose run can
be verified and replayed afterwards. It wraps the `agentic-os` Mission kernel; you keep your own agent framework
and wrap your existing call in a `capability`.

**Who it's for.** Developers who want approval gates, an inspectable plan, and a replayable record around an
existing agent or workflow, and who are comfortable with alpha software.

**Maturity: alpha** (`Development Status :: 3 - Alpha`; reference SDK, not a production service; no
independent validation). Status detail, tested vs proposed, and known gaps: [STATUS.md](STATUS.md).

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-Apache--2.0-green)
![status](https://img.shields.io/badge/status-alpha%20(M3)-orange)
[![NVIDIA Inception](https://img.shields.io/badge/NVIDIA-Inception%20Program%20Member-76B900.svg)](https://www.nvidia.com/en-us/startups/)

> Not published on PyPI. No ReDevOps package is published there. Install from a git tag (below).

## 3-minute example

Needs Python 3.11+ and `git` (the SDK installs `agentic-os` from GitHub). No provider key, no network at
run time.

```bash
python -m venv .venv && . .venv/bin/activate
pip install "redevops-mission @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.8"
git clone --depth 1 https://github.com/redevops-io/mission-sdk.git      # for the example files only
python mission-sdk/examples/00_minimal/main.py              # plan, run, explain, replay, verify
python mission-sdk/examples/02_governed_quickstart/main.py  # adds an approval gate and a sealed "receipt"
```

(The example files come from the default branch; the installed package comes from the `v0.3.8` tag.
`02_governed_quickstart` is included from `v0.3.8`.) What was actually run, on which OS and commit, and its exact output:
[docs/QUICKSTART_VERIFIED.md](docs/QUICKSTART_VERIFIED.md).

## Evidence

- CI (`public-tests` workflow): editable install from a clone, `rdo doctor`, examples, replay, adoption tests.
  This does **not** exercise the git-tag install above; that path was checked by hand, see
  [QUICKSTART_VERIFIED.md](docs/QUICKSTART_VERIFIED.md).
- Evidence cards for quantitative statements: [docs/evidence/](docs/evidence/). Every card is labelled
  *Illustrative/synthetic*, *Internally reproduced*, *Externally reproduced* or *Field validated*. None of the
  claims in this repository is externally reproduced or field validated.

## Limitations

Alpha API; single-node local profile by default; hard dependency on `agentic-os` (git pin); no independent validation of any
kind. Full list: [STATUS.md](STATUS.md).

## Naming

One public product name, **ReDevOps Runtime**, made of three parts: *Mission* (governed execution), *Context*
(context selection and optimization) and *Discovery* (finding and prioritizing opportunities). *Agentic Apps*
are applications that use the runtime. *Agentic OS* is the integrated control-plane and deployment surface, not
a fourth runtime. This SDK is the front door to the Mission part. Glossary:
[agentic-os/docs/GLOSSARY.md](https://github.com/redevops-io/agentic-os/blob/main/docs/GLOSSARY.md).

## Docs

[QUICKSTART](QUICKSTART.md) · [STATUS](STATUS.md) · [ARCHITECTURE](ARCHITECTURE.md) · [COMPATIBILITY](COMPATIBILITY.md) ·
[PARITY](PARITY.md) · [SECURITY](SECURITY.md) · [CONTRIBUTING](CONTRIBUTING.md) · [CHANGELOG](CHANGELOG.md) ·
[Examples](examples/) · [For coding agents](AGENTS.md)

---

# Reference

## Install


> `redevops-mission` is **not published to PyPI** (no ReDevOps package is). Install from a git tag or a clone.

```bash
# from a git tag (needs git on PATH)
pip install "redevops-mission @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.8"
# …or from a clone
pip install -e .                      # the SDK + its pinned agentic-os runtime; exposes the `rdo` command
```

Optional adoption extras (`[langgraph]`, `[langchain]`, `[telemetry]`, `[full]`), e.g.
`pip install "redevops-mission[langgraph] @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.8"`. The default
install needs **no provider key and no network** to run the minimal example. Check the environment any time
with `rdo doctor`.

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
# run        : state=succeeded succeeded=True nodes=1
# explain    : goal='Greet the user', 1 node(s), first=greet.hello -> greeting_ready
# replay     : recorded=succeeded replayed=succeeded consistent=True integrity_ok=True
# verify     : succeeded=True integrity_ok=True verifications=0
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

## Public stack vs enterprise extensions

The public `agentic-os` stack (its `LICENSE.md` is titled "source-available, not open source"; see
[Licence](#licence)) is the **runtime contract and reference implementation** — canonical contracts,
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
[CONTRIBUTING](CONTRIBUTING.md).


## Licence

This package: Apache-2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE)). It depends on `agentic-os`, whose
`LICENSE.md` is titled "source-available, not open source" (AGPL-3.0-or-later WITH Commons-Clause). Read both licence files before depending on this package.
