"""`MissionProgram` — the one public artifact a developer holds.

A `MissionProgram` is the portable, versioned, serializable description of a mission: its goal, the
grants it runs under, and its steps (each an outcome to produce, the need that outcome satisfies, and
its dependencies). It is authored via the DSL (`@template` + `step`) and lowered from the runtime's
internal `ExecutionIntent`, which never crosses this boundary. The SDK compiles a `MissionProgram`
against a set of authored capabilities to validate/explain/run/replay it — one path, whether the author
is a human or (later) a Discovery `MissionProposal`.

The serialization is deliberately small and stable; when `runtime-contracts` freezes its canonical
`MissionProgram`, this becomes a thin adapter over the golden fixtures (design §8).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = "0.1"


@dataclass
class MissionStep:
    outcome: str                     # what this step produces (bound to a capability that `provides` it)
    need: str                        # the natural-language need the outcome satisfies
    after: list[str] = field(default_factory=list)        # upstream outcomes this step depends on
    constraints: list[str] = field(default_factory=list)  # e.g. "requires human approval"
    value: str = "medium"


@dataclass
class MissionProposal:
    """A source-agnostic mission description — what a human template, a domain compiler (e.g. Quantify),
    or the Discovery Runtime emits. It compiles to a `MissionProgram` the *same way regardless of source*
    (design §13.3: one compilation path), so a proposed mission is validated, run, replayed and gated
    exactly like a hand-authored one.

    `source` is the *kind* of author (e.g. "discovery", "compiler:quantify"). `origin` is the *why* — the
    specific record that authorized this mission (a Discovery signal, a decision, a requirement), so a
    replay/audit can answer "what triggered this run", not just "what ran". Conventional keys:
    `{"kind": "discovery:signal"|"decision"|"requirement"|..., "ref": "<id>", "detail": "<text>"}`."""
    name: str
    goal: str
    steps: list[MissionStep] = field(default_factory=list)
    grants: list[str] = field(default_factory=list)
    source: str = "unknown"
    origin: dict | None = None


@dataclass
class MissionProgram:
    name: str
    goal: str
    grants: list[str] = field(default_factory=list)
    steps: list[MissionStep] = field(default_factory=list)
    source: str = "human:template"
    origin: dict | None = None          # the triggering record (the "why"); see MissionProposal
    schema_version: str = SCHEMA_VERSION

    # ---- authoring ---------------------------------------------------------------------------------
    @classmethod
    def from_template(cls, template_name: str, *, goal: str, grants: list[str],
                      source: str = "human:template", origin: dict | None = None) -> "MissionProgram":
        """Lower a registered `@template` into a `MissionProgram` (the internal `ExecutionIntent` stays
        internal). `source`/`origin` let a non-human author (e.g. Discovery) reuse a template and still
        stamp provenance."""
        from .authoring import build_intent

        intent = build_intent(template_name, mission_id="draft")
        steps = [
            MissionStep(outcome=s.outcome, need=s.need, after=list(s.inputs_from),
                        constraints=list(s.constraints), value=s.value_hint)
            for s in intent.steps
        ]
        return cls(name=template_name, goal=goal, grants=list(grants), steps=steps,
                   source=source, origin=origin)

    @classmethod
    def from_discovery(cls, proposal: dict, *, grants: list[str]) -> "MissionProgram":
        """Compile a **Discovery Runtime proposal** onto the one compilation path (design §13.3). Discovery
        proposes a `suggested_template` + goal (not steps), so this lowers that template into a
        `MissionProgram` stamped with the proposal as `origin` — a discovered mission then validates, runs,
        replays and gates **exactly like a hand-authored one**, resolving the two-`MissionProposal`
        collision (Discovery no longer needs a bespoke `create_mission` bridge).

        Decoupled by design: it takes the proposal as a **dict**, not the enterprise Discovery type, so the
        public SDK never depends on the enterprise runtime. Expected keys: `suggested_template` (or
        `template`), `goal`, and optionally `id`, `opportunity_class`, `hypothesis_id`, `score`, `priority`."""
        template = proposal.get("suggested_template") or proposal["template"]
        origin = {"kind": "discovery:proposal", "ref": proposal.get("id", ""),
                  "opportunity_class": proposal.get("opportunity_class", ""),
                  "hypothesis_id": proposal.get("hypothesis_id", ""),
                  "score": proposal.get("score"), "priority": proposal.get("priority", "medium")}
        return cls.from_template(template, goal=proposal.get("goal", ""), grants=grants,
                                 source="discovery", origin=origin)

    @classmethod
    def from_proposal(cls, proposal: "MissionProposal") -> "MissionProgram":
        """The single compilation path for a non-human source: a Discovery `MissionProposal` or a domain
        compiler's output becomes a `MissionProgram`, carrying its provenance. From here it is identical
        to a hand-authored program — same validate / run / replay / ci."""
        return cls(name=proposal.name, goal=proposal.goal, grants=list(proposal.grants),
                   steps=[MissionStep(**{**vars(s)}) for s in proposal.steps],
                   source=proposal.source, origin=proposal.origin)

    # ---- serialization -----------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, d: dict) -> "MissionProgram":
        return cls(
            name=d["name"], goal=d.get("goal", ""), grants=list(d.get("grants", [])),
            steps=[MissionStep(**s) for s in d.get("steps", [])],
            source=d.get("source", "human:template"), origin=d.get("origin"),
            schema_version=d.get("schema_version", SCHEMA_VERSION),
        )

    @classmethod
    def from_json(cls, text: str) -> "MissionProgram":
        return cls.from_dict(json.loads(text))
