# Runtime parity — can the *published* runtime satisfy the Mission SDK's contract?

**Question (narrow, by design):** not "are the repos equal" but "can the public `agentic-os` runtime
satisfy the Mission SDK's public dependency contract?" Checked against the SDK's *actual* import surface
only.

**Checkouts:** public `redevops-io/agentic-os` @ `b43d11c` (`main`, **post open-core migration** — the
versioned public contracts `merge/v9` · `execution-plan/v8` · `runtime-event/v10` · `control-plane/v9` ·
`topology/v8` · `evaluation/v10` · `overlays/v8` are all merged) vs the development runtime
`redevops-io/agentic-os-enterprise` (post namespace-split, which now **references** this public core).

**Licensing:** the SDK is **Apache-2.0** (permissive — the developer boundary + compatibility target);
the reference runtime `agentic-os` is **AGPL-3.0** (running the SDK against it carries the runtime's AGPL
for a served combined work).

**Re-verified 2026-09-12** against public `agentic-os` `main` @ `0c6fb0c` (240 commits past the prior pin
`63c0b25`, spanning the outcome/learning-loop + governed-assist line of work): the SDK's **11-module import
surface is unchanged** (all symbols/methods present), and the **full SDK suite is 43 passed** (with
`runtime_contracts` on the path — the `security_monitor` telemetry tests import it as an opt-in capability;
it is *not* in the SDK's own dependency surface). Pin bumped to `0c6fb0c` accordingly.

## The SDK's actual dependency surface

`redevops_mission` imports **11 modules** from the runtime — directly:

| Module → symbols the SDK uses | in public? | signature vs src | verdict |
|---|---|---|---|
| `mission.sdk` → `step`, `template` | ✅ | identical | ✅ |
| `mission.operator_sdk` → `Operator`, `capability`, `LocalOperatorClient` | ✅ | identical | ✅ |
| `mission.compiler` → `CompileError`, `compile_intent` | ✅ | src adds optional `axes=` (superset) | ✅ SDK calls the 3-arg form |
| `mission.simulator` → `simulate` | ✅ | identical | ✅ |
| `mission.mission_ci` → `run_mission_ci` | ✅ | identical | ✅ |
| `mission.registry` → `CapabilityRegistry` (`register`, `get`) | ✅ | identical | ✅ |
| `mission.runtime` → `MissionRuntime` (`create_mission`, `run`, `approve`, `rehydrate`, `inbox`) | ✅ | src adds enterprise kwargs `identity_plane/metering/budget_guard`, `principal/tenant` (superset) | ✅ SDK uses none |
| `mission.store` → `EventStore` (`append`, `for_mission`, `all`) | ✅ | identical | ✅ |
| `mission.templates` → `TEMPLATES` | ✅ | identical (dict contract) | ✅ |
| `mission.types` → `ExecutionIntent`, `IntentStep`, `Mission`, `SimResult`, `Node`, `CapabilitySpec`, … | ✅ | `Mission` adds `principal/tenant`; `ExecutionPlan` is the fuller enterprise shape (superset) | ✅ SDK constructs only Intent/Step/Mission; reads only `plan.graph`/`plan.id` |
| `mission.executor` → `Executor` | ✅ | identical | ✅ |

**Transitive closure:** importing these pulls in `planner`, `verify`, `context`, `scheduler`, … but
**not `events`**. As of the open-core migration `agentic_os.mission.events` (the v10 `RuntimeEvent` family,
`runtime-event/v10`) is **now public**, but it stays **outside the SDK's surface** — the SDK builds case
bundles over the operational `EventStore`, not the event vocabulary. The 11-module import surface above is
unchanged by the migration; every module the SDK touches is public and satisfies the contract.

**`runtime-contracts`:** not in the SDK's surface — the SDK uses `agentic_os.mission` types directly, so
there is nothing to pin there yet.

**Every signature difference is `agentic-os-src` (enterprise) being a strict superset** — extra optional
enterprise parameters the SDK does not pass. Nothing the SDK depends on is missing or divergent in public.

## Behavioral gates — all five dogfood shapes on the PUBLIC runtime

`PYTHONPATH=<public agentic-os @ b43d11c>` — full test suite **28 passed**, and every verb ran on every shape:

| shape | validate | explain | profile | simulate | run | bundle | replay | verify | ci |
|---|---|---|---|---|---|---|---|---|---|
| saga (revenue_rescue) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| merge+verify (dataops_reconcile) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| gated pipeline (deploy_release) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| scaffolded (`init`) | ✅ | — | — | — | ✅ | — | — | — | ✅ |
| **compiler-emitted (from_proposal)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

The compiler-emitted case is the important one: it proves `MissionProgram.from_proposal(...)` does not
depend on `@template` registration, on the public runtime.

**A real bug the parity check surfaced (SDK, not a gap):** cross-process `replay` of a `from_proposal`
mission failed under *both* runtimes — the runtime's `rehydrate` re-compiles the plan and needs the
template, which a fresh process (no `@template`) lacks. Fixed by making the case bundle self-carry its
step definitions and re-registering on replay. Now consistent cross-process under both runtimes.

## Verdict & pinning decision

**Exact behavioral parity** for the SDK's contract — the public runtime satisfies it fully, and the
contracts the SDK rides on are **versioned and public** (`execution-plan/v8`, `runtime-event/v10`, …).

The SDK pins a runtime **release tag**. The runtimes are versioned on the **`v0.3.x`** line (release tags
lead the pyproject version by convention — agentic-os reports `0.2.4` in metadata while its releases are
tagged `v0.3.0`, `v0.3.1`, …), so a PEP 440 `agentic-os==0.3.1` specifier would not match the package
metadata; the SDK pins the **git tag** instead:

```
agentic-os @ git+https://github.com/redevops-io/agentic-os.git@v0.3.1
```

`v0.3.1` is the release cut at `0c6fb0c` — the exact commit this parity check verified. Reproducible and
honest. **Next step:** once agentic-os's package metadata is aligned to the `v0.3.x` tags, the SDK can move
to a PEP 440 `agentic-os==0.3.x` specifier, and begin pinning `runtime-contracts` versions directly once its
surface consumes them. `_bootstrap` is a **loud, opt-in dev fallback** (only via `AGENTIC_OS_SRC`), never a
silent compatibility layer.
