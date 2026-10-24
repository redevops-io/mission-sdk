# Quickstart: what was actually run

Only commands that were executed are listed here. Date: 2026-10-15.

## Environment

| Item | Value |
|---|---|
| Container | `docker run --rm python:3.12-slim` (Docker Engine 29.9.0) |
| OS / arch | Debian GNU/Linux 13 (trixie), `Linux 7.0.0-38-generic x86_64` |
| Python | 3.12.14 |
| Provider keys | none (`env | grep -iE "api_key|token"` printed nothing) |
| Package installed from | git tag `v0.3.7` of `redevops-io/mission-sdk` (pulls `agentic-os` tag `v0.3.31`) |
| Example files from | commit `e9b8fad499cc15e19576b6730e9e017555da35cb` (the `Release 0.3.7 (#20)` commit that `v0.3.7` points at) plus the new `examples/02_governed_quickstart/main.py` from this change, mounted read-only |
| Network | outbound HTTPS to github.com and the Debian mirror was available |

## Finding: `git` is required and is not in `python:3.12-slim`

The first attempt shows `git` is absent from the image (`which git` printed nothing). `pip install ... @ git+https://...`
needs it, so the script installs it with `apt-get install -y git` first. Hence the README states that `git` is
required. Also `pip` is 25.0.1 in that image; the install worked with it.

## Commands and output

```bash
apt-get update -qq && apt-get install -y -qq git          # git version 2.47.3
python -m venv /venv
/venv/bin/pip install -q "redevops-mission @ git+https://github.com/redevops-io/mission-sdk.git@v0.3.7"
env | grep -iE "api_key|token" || echo "no provider keys in env"
/venv/bin/rdo doctor
/venv/bin/python /work/examples/00_minimal/main.py
/venv/bin/python /work/examples/02_governed_quickstart/main.py
```

Output (install progress and debconf noise omitted):

```text
no provider keys in env
ReDevOps Mission SDK - doctor

  mission-sdk        0.3.7                        OK
  python             3.12.14                      OK
  agentic-os         0.3.31                       OK
  minimal mission    runs                         OK

All checks passed - the SDK is ready.
run        : state=succeeded succeeded=True nodes=1
explain    : goal='Greet the user', 1 node(s), first=greet.hello -> greeting_ready
replay     : recorded=succeeded replayed=succeeded consistent=True integrity_ok=True
verify     : succeeded=True integrity_ok=True verifications=0

OK - mission executed, explained, replayed, and verified.
explain  : goal='Publish the maintenance notice', 2 node(s)
           notice.draft -> notice_drafted
           notice.publish -> notice_published
no approval : state=waiting_human succeeded=False pending_gates=1
approved    : state=succeeded succeeded=True approvals_applied=1
receipt     : integrity_ok=True succeeded=True
replay      : recorded=succeeded replayed=succeeded consistent=True

OK - planned, gated, approved, sealed, verified, replayed.
```

(The doctor banner uses an em dash in the real output; ASCII is shown here.)

## Test suite (fresh venv, not the container)

In a fresh `uv venv --python 3.12` under `/mnt/backup/projects/_worktrees/venv-msdk` (Linux x86_64, host
Python 3.12.13), with the package installed from the same `v0.3.7` tag and the repository's `tests/` directory
from commit `e9b8fad`: `python -m pytest -q` -> `44 passed in 0.54s`.

## Not verified

- Anything on macOS or Windows, or other Python versions (3.11 is the declared minimum; 3.12 only was run).
- The optional extras (`[langgraph]`, `[langchain]`, `[telemetry]`).
- The `rdo mission ...` CLI verbs from `QUICKSTART.md` were not run in the container (they run in this
  repository's CI via the `quickstart` job, editable install).
- Any provider-backed or networked run.
