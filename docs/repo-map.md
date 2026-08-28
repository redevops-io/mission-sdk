# Repo map — which repository owns what

The ReDevOps Runtime is a multi-repo stack. `mission-sdk` is the **public front door**: it owns onboarding,
composition, and examples, and it *links* to each canonical repo — it does not fork their implementations or
docs.

| Repository | Public responsibility | Canonical for |
|---|---|---|
| **`mission-sdk`** (this repo) | application-facing SDK, onboarding, examples, composition, public conformance smoke tests | the developer boundary + adoption experience |
| `runtime-contracts` | canonical cross-runtime contracts | `ContextView`, `EvidenceRef`, `EvidenceChange`, plan/handle identity |
| `discovery-runtime` | discovery / intent / evidence | intent classification, evidence identity |
| `context-runtime` | context selection + method/model optimization | retrieval routing, materialization depth, plan-cache identity, tenant isolation |
| `agentic-os` | Mission execution engine, replay, governance | the Mission runtime `mission-sdk` drives (plan → execute → verify → replay → govern) |
| `redevops-rag` | retrieval capabilities | hybrid/vector/BM25 retrieval used as capabilities |
| enterprise repos | private enforcement / plugins | production security enforcement, telemetry bridges, secret stores, deployment adapters |

**Rule:** `mission-sdk` links to canonical docs; it does not restate implementation-specific documentation
unless required for SDK use. If you need internals of a subsystem, follow the link to its owning repo above.

## What you import from where

- From `redevops_mission` (this repo): everything an application needs — see [AGENTS.md](../AGENTS.md#public-surface-safe-to-import).
- From `agentic_os.*`: **only** if you are implementing runtime internals. Application code should not.
- Enterprise plugins are **optional** and never required for public SDK use — see the open-core note in the
  [README](../README.md#public-agpl-stack-vs-enterprise-extensions).

## Versions

The exact compatible versions of each repo are pinned per `mission-sdk` release and listed in
[COMPATIBILITY.md](../COMPATIBILITY.md). Check your install with `rdo doctor`.
