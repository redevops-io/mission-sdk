# Changelog

No curated changelog has been kept for this repository. The history is:

- Git tags: `v0.1.0-alpha`, `v0.3.0` ... `v0.3.8` (there is no `v0.2.x`): <https://github.com/redevops-io/mission-sdk/tags>
- One GitHub release (`v0.1.0-alpha`): <https://github.com/redevops-io/mission-sdk/releases>
- Per-release commits: `git log --oneline v0.3.7..v0.3.8`, and so on.
- Version and runtime pins per release: [COMPATIBILITY.md](COMPATIBILITY.md).

## Unreleased

- Pin kernel `agentic-os` to `v0.4.2` (was `v0.3.39`, which predates the kernel's 0.4.0 security fixes). The suite, both quickstart examples and
  `rdo doctor` pass unchanged. The 0.4 kernel prints a notice on stderr when `AGENTIC_OS_PROFILE` is unset (it runs as `development`, where
  authority is not enforced); set `AGENTIC_OS_PROFILE=production` for anything that acts on real systems.
- **Fixed: `verify_bundle` passed a bundle whose recorded `state` and `outcome` had been edited.** The digest covered the events only (and kept
  64 bits of the hash), and success was read from the `state` field. A run that stopped at its approval gate could be relabelled `succeeded`
  and still verify. Bundles are now schema `0.2`: the digest is a full SHA-256 over goal, state, outcome, events, steps, source and origin, and
  verify and replay also require the recorded state to be the one the event log ends in. Schema `0.1` bundles still load; their digest is
  reported as covering events only, and the event-log check applies to them too.

## 0.3.8

- Pin kernel `agentic-os` to `v0.3.39` (was `v0.3.31`) so a consumer pinning the current kernel resolves without `--no-deps`.
- Docs: README first screen, STATUS, CONTRIBUTING, verified quickstart, evidence cards, docs check; example
  `examples/02_governed_quickstart`.
