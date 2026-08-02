"""`rdo mission …` — the Mission DevOps CLI.

M0 verbs: `validate` and `explain`. Both load a *mission module* (a `.py` file exposing `PROGRAM`
— a `MissionProgram` — and `OPERATORS` — a list of `Operator`s) and operate on it read-only.

    rdo mission validate examples/revenue_rescue/mission.py
    rdo mission explain  examples/revenue_rescue/mission.py
"""
from __future__ import annotations

import argparse
import importlib.util
import sys

from .api import explain, validate
from ._compile import CompileError


def _load_module(path: str):
    spec = importlib.util.spec_from_file_location("_rdo_mission_module", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load mission module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "PROGRAM") or not hasattr(mod, "OPERATORS"):
        raise SystemExit(
            f"{path} must expose PROGRAM (a MissionProgram) and OPERATORS (a list of Operator)"
        )
    return mod.PROGRAM, mod.OPERATORS


def _cmd_validate(args) -> int:
    program, operators = _load_module(args.target)
    report = validate(program, operators)
    print(report.to_text())
    return 0 if report.passed else 1


def _cmd_explain(args) -> int:
    program, operators = _load_module(args.target)
    try:
        print(explain(program, operators).to_text())
    except CompileError as e:
        print(f"explain: cannot compile — {e}\n(run `rdo mission validate` for the full report)")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rdo", description="ReDevOps developer CLI")
    groups = parser.add_subparsers(dest="group", required=True)

    mission = groups.add_parser("mission", help="author, inspect, and operate missions")
    verbs = mission.add_subparsers(dest="verb", required=True)
    for verb, fn, helptext in (
        ("validate", _cmd_validate, "static + compile checks on a mission module"),
        ("explain", _cmd_explain, "render the compiled physical graph"),
    ):
        p = verbs.add_parser(verb, help=helptext)
        p.add_argument("target", help="path to a mission module (.py exposing PROGRAM + OPERATORS)")
        p.set_defaults(_fn=fn)

    args = parser.parse_args(argv)
    return args._fn(args)


if __name__ == "__main__":
    sys.exit(main())
