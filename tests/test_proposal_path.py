"""One compilation path (design §13.3): a compiler-emitted proposal compiles and operates exactly like
a hand-authored program — same validate / run / ci — and carries its provenance."""
from __future__ import annotations

import importlib.util
import os

from redevops_mission import (
    MissionProgram, MissionProposal, MissionStep, export_bundle, mission_ci, replay_bundle,
    run_program, validate,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, os.pardir, "examples", "from_proposal", "mission.py")


def _load():
    spec = importlib.util.spec_from_file_location("_fp", FIXTURE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_from_proposal_carries_provenance():
    p = MissionProposal(name="m", goal="g", source="discovery",
                        steps=[MissionStep(outcome="done", need="do it")], grants=[])
    program = MissionProgram.from_proposal(p)
    assert program.source == "discovery"
    assert program.name == "m" and program.steps[0].outcome == "done"


def test_compiler_emitted_mission_validates_runs_and_gates():
    m = _load()
    assert m.PROGRAM.source == "compiler:quantify"          # provenance survived
    assert validate(m.PROGRAM, m.OPERATORS).passed          # same validate as a hand-authored program
    assert run_program(m.PROGRAM, m.OPERATORS, approve=True).succeeded
    r = mission_ci(m.PROGRAM, m.OPERATORS)
    assert r.passed                                         # same ci gate, regardless of source


def test_proposal_program_json_roundtrip_keeps_source():
    m = _load()
    rt = MissionProgram.from_json(m.PROGRAM.to_json())
    assert rt.source == "compiler:quantify"
    assert rt.to_dict() == m.PROGRAM.to_dict()


def test_replay_of_proposal_is_self_contained_in_a_fresh_process():
    """A from_proposal mission has no @template, so a fresh process (or a cleared registry) has nothing
    registered. Replay must reconstruct the template from the bundle's own steps — the runtime's
    rehydrate re-compiles the plan. This is the cross-process case the parity check surfaced."""
    from agentic_os.mission.templates import TEMPLATES

    m = _load()
    b = export_bundle(m.PROGRAM, m.OPERATORS)          # succeeds; carries its step definitions
    TEMPLATES.pop(m.PROGRAM.name, None)                # forget the dynamically-registered template
    r = replay_bundle(b, m.OPERATORS)                  # must re-register from bundle.steps
    assert r.consistent and r.integrity_ok
    assert r.recorded_state == r.replayed_state == "succeeded"
