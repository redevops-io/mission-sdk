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

from .api import explain, profile, simulate, validate
from ._compile import CompileError
from .profiles import run_program


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


def _cmd_simulate(args) -> int:
    program, operators = _load_module(args.target)
    try:
        report = simulate(program, operators)
    except CompileError as e:
        print(f"simulate: cannot compile — {e}\n(run `rdo mission validate` for the full report)")
        return 1
    print(report.to_text())
    return 0 if report.within_budget else 1


def _cmd_profile(args) -> int:
    program, operators = _load_module(args.target)
    try:
        print(profile(program, operators).to_text())
    except CompileError as e:
        print(f"profile: cannot compile — {e}\n(run `rdo mission validate` for the full report)")
        return 1
    return 0


def _cmd_run(args) -> int:
    program, operators = _load_module(args.target)
    result = run_program(program, operators, approve=args.approve, ledger_path=args.ledger)
    print(result.to_text())
    if result.succeeded:
        return 0
    return 2 if result.state == "waiting_human" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rdo", description="ReDevOps developer CLI")
    groups = parser.add_subparsers(dest="group", required=True)

    mission = groups.add_parser("mission", help="author, inspect, and operate missions")
    verbs = mission.add_subparsers(dest="verb", required=True)
    for verb, fn, helptext in (
        ("validate", _cmd_validate, "static + compile checks on a mission module"),
        ("explain", _cmd_explain, "render the compiled physical graph"),
        ("profile", _cmd_profile, "EXPLAIN ANALYZE — topology + projected cost/latency/success"),
        ("simulate", _cmd_simulate, "dry-run projection (no execution, no model calls)"),
        ("run", _cmd_run, "execute on the local single-node profile"),
    ):
        p = verbs.add_parser(verb, help=helptext)
        p.add_argument("target", help="path to a mission module (.py exposing PROGRAM + OPERATORS)")
        if verb == "run":
            p.add_argument("--approve", action="store_true",
                           help="auto-approve human gates and drive to completion")
            p.add_argument("--ledger", metavar="PATH", default=None,
                           help="persist the event ledger to an append-only file (default: in-memory)")
        p.set_defaults(_fn=fn)

    args = parser.parse_args(argv)
    return args._fn(args)


if __name__ == "__main__":
    sys.exit(main())
