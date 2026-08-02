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
from .bundle import CaseBundle, diff_bundles, diff_text, export_bundle, replay_bundle, verify_bundle
from .ci import mission_ci
from .profiles import run_program
from .scaffold import init_mission


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


def _cmd_bundle(args) -> int:
    program, operators = _load_module(args.target)
    bundle = export_bundle(program, operators)
    if args.out:
        with open(args.out, "w") as f:
            f.write(bundle.to_json())
        print(f"bundle: wrote {len(bundle.events)} events → {args.out}  (state={bundle.state}, digest={bundle.digest})")
    else:
        print(bundle.to_json())
    return 0


def _cmd_replay(args) -> int:
    _, operators = _load_module(args.target)
    with open(args.bundle) as f:
        bundle = CaseBundle.from_json(f.read())
    result = replay_bundle(bundle, operators)
    print(result.to_text())
    return 0 if result.consistent else 1


def _cmd_diff(args) -> int:
    with open(args.a) as f:
        a = CaseBundle.from_json(f.read())
    with open(args.b) as f:
        b = CaseBundle.from_json(f.read())
    print(diff_text(diff_bundles(a, b)))
    return 0


def _cmd_ci(args) -> int:
    program, operators = _load_module(args.target)
    result = mission_ci(program, operators)
    print(result.to_text())
    return 0 if result.passed else 1


def _cmd_init(args) -> int:
    try:
        path = init_mission(args.name, args.dir)
    except (ValueError, FileExistsError) as e:
        print(f"init: {e}")
        return 1
    print(f"init: wrote {path}\n"
          f"  next:  rdo mission validate {path}\n"
          f"         rdo mission run      {path} --approve")
    return 0


def _cmd_verify(args) -> int:
    program, operators = _load_module(args.target)
    report = verify_bundle(export_bundle(program, operators))
    print(report.to_text())
    return 0 if report.succeeded and report.integrity_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rdo", description="ReDevOps developer CLI")
    groups = parser.add_subparsers(dest="group", required=True)

    mission = groups.add_parser("mission", help="author, inspect, and operate missions")
    verbs = mission.add_subparsers(dest="verb", required=True)

    TARGET = "path to a mission module (.py exposing PROGRAM + OPERATORS)"

    # read-only + run verbs, all taking a single mission-module target
    for verb, fn, helptext in (
        ("validate", _cmd_validate, "static + compile checks on a mission module"),
        ("explain", _cmd_explain, "render the compiled physical graph"),
        ("profile", _cmd_profile, "EXPLAIN ANALYZE — topology + projected cost/latency/success"),
        ("simulate", _cmd_simulate, "dry-run projection (no execution, no model calls)"),
        ("run", _cmd_run, "execute on the local single-node profile"),
        ("verify", _cmd_verify, "run + report what the runtime verified (success, integrity, stages)"),
        ("ci", _cmd_ci, "promotion gate: feasibility · budget · run · regression · replay"),
    ):
        p = verbs.add_parser(verb, help=helptext)
        p.add_argument("target", help=TARGET)
        if verb == "run":
            p.add_argument("--approve", action="store_true",
                           help="auto-approve human gates and drive to completion")
            p.add_argument("--ledger", metavar="PATH", default=None,
                           help="persist the event ledger to an append-only file (default: in-memory)")
        p.set_defaults(_fn=fn)

    pb = verbs.add_parser("bundle", help="run + export a portable, self-verifying case bundle")
    pb.add_argument("target", help=TARGET)
    pb.add_argument("--out", metavar="PATH", default=None, help="write the bundle JSON here (default: stdout)")
    pb.set_defaults(_fn=_cmd_bundle)

    pr = verbs.add_parser("replay", help="rebuild a run from its bundle and confirm the terminal state")
    pr.add_argument("target", help=TARGET)
    pr.add_argument("bundle", help="path to a case bundle JSON")
    pr.set_defaults(_fn=_cmd_replay)

    pd = verbs.add_parser("diff", help="structural diff of two case bundles")
    pd.add_argument("a", help="case bundle JSON")
    pd.add_argument("b", help="case bundle JSON")
    pd.set_defaults(_fn=_cmd_diff)

    pi = verbs.add_parser("init", help="scaffold a runnable starter mission")
    pi.add_argument("name", help="mission name (a valid Python identifier)")
    pi.add_argument("--dir", default=".", help="directory to create the mission project in (default: .)")
    pi.set_defaults(_fn=_cmd_init)

    args = parser.parse_args(argv)
    return args._fn(args)


if __name__ == "__main__":
    sys.exit(main())
