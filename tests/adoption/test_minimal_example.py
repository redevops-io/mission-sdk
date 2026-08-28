"""Adoption guarantee: the 00_minimal example works from a clean install.

These are the public tests behind the README/QUICKSTART claim "one URL is enough to go from
unfamiliarity to a running, testable integration". The example is loaded from disk (not re-authored) so a
broken example fails CI. Offline + deterministic — no provider keys, no network.
"""
from __future__ import annotations

import importlib.util
import pathlib

from redevops_mission import export_bundle, replay_bundle, run_program, verify_bundle

_EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "00_minimal" / "main.py"


def _load_example():
    spec = importlib.util.spec_from_file_location("minimal_example", _EXAMPLE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)   # defines PROGRAM/OPERATORS; main() only runs under __main__
    return mod


EX = _load_example()


def test_minimal_mission_executes_without_framework_rewrite():
    result = run_program(EX.PROGRAM, EX.OPERATORS)
    assert result.succeeded
    assert result.nodes_succeeded == 1


def test_replay_reuses_sealed_plan():
    bundle = export_bundle(EX.PROGRAM, EX.OPERATORS)
    replay = replay_bundle(bundle, EX.OPERATORS)
    assert replay.consistent and replay.integrity_ok
    assert replay.recorded_state == replay.replayed_state


def test_bundle_is_self_verifying():
    report = verify_bundle(export_bundle(EX.PROGRAM, EX.OPERATORS))
    assert report.succeeded and report.integrity_ok
