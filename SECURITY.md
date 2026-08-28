# Security

## Scope

`redevops-mission` (the Mission SDK) is the developer boundary over the ReDevOps Mission Runtime. This policy
covers the SDK and its public examples/tests. The runtime engine (`agentic-os`) and the enterprise extensions
carry their own policies in their own repositories.

## Reporting a vulnerability

Report privately — do **not** open a public issue for a suspected vulnerability. Use GitHub's **Report a
vulnerability** (Security → Advisories) on this repo, or email the maintainers. Include a description, the
affected version (`rdo doctor` output helps), and a minimal reproduction. Expect an acknowledgement within a
few business days and a coordinated disclosure once a fix is available.

## What the SDK does and does not do

- The SDK executes missions on a **local single-node profile** by default. The minimal example needs **no
  provider key and no network** — running it does not transmit anything off the machine.
- **Approval-gated capabilities** (e.g. anything that publishes or causes an external side effect) require an
  explicit approval; they never fire implicitly. Treat a mission module as executable code and review it as
  such before `rdo mission run`.
- **Bundles** (`export_bundle` / `rdo mission bundle`) capture the mission's plan, events, and terminal state
  for replay. Do not commit a bundle that embedded secrets or private data into its recorded inputs — inspect
  before sharing.
- The v0.3.x **security/telemetry plane** (`--secure`) is opt-in; it wires boundary telemetry and
  containment. It is never required for basic use and is off by default.

## Secrets

Never hard-code credentials in a mission module or an example. Handlers should read secrets from the
environment or a secret store at call time. The public examples deliberately use no secrets.

## Supported versions

This is alpha (M3). Security fixes land on the latest `0.2.x` line; there is no long-term support branch yet.
