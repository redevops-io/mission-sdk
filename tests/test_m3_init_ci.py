"""M3: `init` scaffolds a runnable mission; `ci` gates the fixtures and catches a broken one."""
from __future__ import annotations

import importlib.util
import os

from redevops_mission import MissionProgram, init_mission, mission_ci, run_program, validate

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, os.pardir, "examples")


def _load_path(path, name="_m"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_example(name):
    return _load_path(os.path.join(EXAMPLES, name, "mission.py"), f"_ex_{name}")


# ---- init scaffolds something that actually validates and runs ---------------------------------------
def test_init_scaffolds_runnable_mission(tmp_path):
    path = init_mission("demo_mission", str(tmp_path))
    assert os.path.isfile(path)
    mod = _load_path(path, "_scaffolded")
    assert validate(mod.PROGRAM, mod.OPERATORS).passed
    assert run_program(mod.PROGRAM, mod.OPERATORS, approve=True).succeeded


def test_init_rejects_bad_name(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        init_mission("not a name", str(tmp_path))


def test_init_refuses_overwrite(tmp_path):
    import pytest
    init_mission("dup", str(tmp_path))
    with pytest.raises(FileExistsError):
        init_mission("dup", str(tmp_path))


# ---- ci gates the fixtures ---------------------------------------------------------------------------
def test_ci_passes_on_fixtures():
    for name in ("revenue_rescue", "dataops_reconcile", "deploy_release"):
        m = _load_example(name)
        r = mission_ci(m.PROGRAM, m.OPERATORS)
        assert r.passed, f"{name}: {r.checks}"
        assert {c[0] for c in r.checks} == {"feasibility", "budget", "run", "regression", "replay"}


def test_ci_fails_on_missing_grant():
    m = _load_example("revenue_rescue")
    broken = MissionProgram.from_dict({**m.PROGRAM.to_dict(), "grants": ["support:write"]})
    r = mission_ci(broken, m.OPERATORS)
    assert not r.passed
    assert any(name == "feasibility" and not ok for name, ok, _ in r.checks)
