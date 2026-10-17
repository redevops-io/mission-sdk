# Changelog

No curated changelog has been kept for this repository. The history is:

- Git tags: `v0.1.0-alpha`, `v0.3.0` ... `v0.3.8` (there is no `v0.2.x`): <https://github.com/redevops-io/mission-sdk/tags>
- One GitHub release (`v0.1.0-alpha`): <https://github.com/redevops-io/mission-sdk/releases>
- Per-release commits: `git log --oneline v0.3.7..v0.3.8`, and so on.
- Version and runtime pins per release: [COMPATIBILITY.md](COMPATIBILITY.md).

## 0.3.8

- Pin kernel `agentic-os` to `v0.3.39` (was `v0.3.31`) so a consumer pinning the current kernel resolves without `--no-deps`.
- Docs: README first screen, STATUS, CONTRIBUTING, verified quickstart, evidence cards, docs check; example
  `examples/02_governed_quickstart`.
