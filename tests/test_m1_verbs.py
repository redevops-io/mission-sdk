"""M1: simulate / profile / run over the local single-node profile, on both dogfood fixtures."""
from __future__ import annotations

import importlib.util
import os

from redevops_mission import profile, run_program, simulate, validate

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, os.pardir, "examples")


def _load(name):
    path = os.path.join(EXAMPLES, name, "mission.py")
    spec = importlib.util.spec_from_file_location(f"_ex_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- Revenue Rescue: has a human gate ----------------------------------------------------------------
def test_revenue_rescue_simulate():
    m = _load("revenue_rescue")
    r = simulate(m.PROGRAM, m.OPERATORS)
    assert r.expected_approvals == 1          # the dunning gate
    assert r.within_budget


def test_revenue_rescue_profile():
    m = _load("revenue_rescue")
    p = profile(m.PROGRAM, m.OPERATORS)
    assert p.topo["nodes"] == 4
    assert p.topo["max_parallelism"] == 2     # reply + campaign run in parallel
    assert p.topo["merge_points"] == 1        # reconciliation folds both branches back in
    assert p.topo["human_gates"] == 1
    assert p.topo["undo_covered"] == p.topo["side_effecting"]  # every side effect has an undo


def test_revenue_rescue_run_parks_then_completes():
    m = _load("revenue_rescue")
    parked = run_program(m.PROGRAM, m.OPERATORS)          # default: no auto-approve
    assert parked.state == "waiting_human"
    assert parked.pending and parked.pending[0]["capability"] == "billing.dunning"

    done = run_program(m.PROGRAM, m.OPERATORS, approve=True)
    assert done.succeeded and done.approvals_applied == 1
    assert done.outcome["world"]["reconciliation_staged"]


# ---- DataOpsBench S21: no gate, read/compute -------------------------------------------------------
def test_dataops_reconcile_validates_and_runs():
    m = _load("dataops_reconcile")
    assert validate(m.PROGRAM, m.OPERATORS).passed
    p = profile(m.PROGRAM, m.OPERATORS)
    assert p.topo["nodes"] == 4
    assert p.topo["max_parallelism"] == 2     # the two per-source extractions
    assert p.topo["merge_points"] == 1        # the governed merge unions both sources
    assert p.topo["human_gates"] == 0 and p.topo["side_effecting"] == 0

    done = run_program(m.PROGRAM, m.OPERATORS)  # no gate -> runs straight through
    assert done.succeeded
    assert done.outcome["world"]["conflicts_detected"] == {"conflicts": ["cm_0"]}
