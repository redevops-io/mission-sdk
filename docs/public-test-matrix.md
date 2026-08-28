# Public test matrix — what the tests prove

The public test suite is grouped by **user-facing guarantee**, not by internal module, so an external
evaluator (or coding agent) can read the guarantees from the test names. Run the whole suite with
`python -m pytest -q`, or a group with e.g. `python -m pytest tests/adoption -q`.

| Guarantee | Public test | Group | Status |
|---|---|---|---|
| A clean install runs the minimal mission | `test_minimal_mission_executes_without_framework_rewrite` | `adoption` | pass |
| Replay reproduces the sealed run | `test_replay_reuses_sealed_plan` | `adoption` | pass |
| A case bundle is self-verifying | `test_bundle_is_self_verifying` | `adoption` | pass |
| An existing agent runs without a framework rewrite | `examples/01_existing_agent` (+ adoption test) | `adoption` | pass |
| Missions execute end-to-end (dogfood fixtures) | `test_revenue_rescue`, `test_video_ad_mission_e2e`, … | `execution` | pass |
| The v0.3.x security/telemetry plane is opt-in | `test_security_telemetry` | `security` | pass |
| Discovery → mission path | `test_discovery_path`, `test_proposal_path` | `interoperability` | pass |

## What the public tests prove (README summary)

- installation works from a clean environment;
- the minimal mission executes offline and deterministically;
- an existing agent can be wrapped without a rewrite;
- replay reproduces the sealed plan/terminal state;
- a case bundle verifies its own integrity without re-running;
- the security/telemetry plane is opt-in, not required for basic use.

## Still to add (tracked against the readiness plan §12)

These are named in the enhancement plan and land as the corresponding capabilities are surfaced publicly
through the SDK:

- `test_default_plan_identity_is_byte_identical` — the compatibility invariant that inactive optimization
  features do not change existing plan identity (owned by `context-runtime`; exposed here when the SDK
  surfaces the optimizer).
- `test_cross_tenant_plan_cache_is_isolated` — the security regression that one tenant's authorized plan is
  never served to another (owned by `context-runtime`; already enforced there, mirrored here when surfaced).
- `test_provider_swap_preserves_mission_semantics` — same mission under two provider adapters.

Until surfaced through `redevops_mission`, these guarantees live in their owning repos (see
[repo-map.md](repo-map.md)); this matrix links out rather than duplicating them.
