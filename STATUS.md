# Status

Last verification date: **2026-10-15**. Package version `0.3.8` (`redevops_mission.__version__`).

**Maturity: alpha.** Reference SDK. Not a production service. Not independently validated.

## Shipped and tested

| Capability | Evidence |
|---|---|
| Author a `MissionProgram` (`template`, `step`, `capability`, `Operator`) and run it on a local single-node profile | `examples/00_minimal`, CI `public-tests` |
| Approval gate: an `approval_required` capability parks the run until approved | `examples/02_governed_quickstart` (run in a clean container, [quickstart-verified](docs/quickstart-verified.md)) |
| `explain` / `validate` / `simulate` / `profile` without execution | `tests/`, CI `quickstart` job |
| Sealed case bundle, `verify_bundle`, `replay_bundle` | `examples/00_minimal`, `tests/adoption` |
| `rdo` CLI verbs (`init validate explain profile simulate run bundle replay ci doctor`) | CI `quickstart` and `replay` jobs |
| Test suite | `python -m pytest -q` -> 44 passed (2026-10-15, fresh venv, see quickstart-verified) |

## Proposed / not claimed

- Anything described as "production": no production deployment of this SDK is claimed here.
- Enterprise extensions (security enforcement, telemetry bridges, deployment adapters) live in private
  repositories and are out of scope for this repository.
- A published PyPI package: none exists.

## Limitations

- Alpha API; names and signatures may change between `0.3.x` tags.
- Hard dependency on `agentic-os` through a git pin (`pyproject.toml`), so installing needs `git` and GitHub access.
- Default execution is local and single node. "Receipt" in these docs means the sealed `CaseBundle`; the SDK
  has no class by that name.
- Licence: this package is Apache-2.0; the `agentic-os` dependency has its own `LICENSE.md` (titled
  "source-available, not open source"). Read both before depending on this package.

## Known gaps

- CI installs with `pip install -e .` from a clone; it does not install from a git tag. The tag install was
  checked by hand once (2026-10-15).
- Tested on Linux x86_64 with Python 3.12 only (declared minimum 3.11).
- `COMPATIBILITY.md` pins are maintained by hand.
- GitHub has one release (`v0.1.0-alpha`) while tags run to `v0.3.8`; see [CHANGELOG](CHANGELOG.md).

## Evidence

[docs/evidence/](docs/evidence/) (claim cards) · [docs/quickstart-verified.md](docs/quickstart-verified.md) ·
[docs/public-test-matrix.md](docs/public-test-matrix.md) · CI: `.github/workflows/public-tests.yml`.
