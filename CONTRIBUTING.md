# Contributing

This repository is documentation-heavy and alpha. Small, reviewable pull requests are welcome.

1. Fork and branch from `main`.
2. `pip install -e . pytest` (needs `git`; the SDK installs `agentic-os` from GitHub). For a local runtime
   checkout set `AGENTIC_OS_SRC=/path/to/agentic-os`.
3. `python -m pytest -q` and `python scripts/docs_check.py` must pass.
4. Docs rules: no claim without a link to an artifact or a label from the four evidence classes
   (*Illustrative/synthetic*, *Internally reproduced*, *Externally reproduced*, *Field validated*); add a card
   under `docs/evidence/` for any new number. Do not describe licences beyond quoting the LICENSE file.
5. Security issues: see [SECURITY.md](SECURITY.md), do not open a public issue.

Licence of contributions follows the repository [LICENSE](LICENSE).
