"""Deploy Release — the net-new dogfood fixture (#3), authored purely from the SDK docs.

A linear release pipeline with one human gate: build the artifact → run tests → [approval] publish →
announce. It exists to check that someone who did *not* build the runtime can express a fresh mission
from the README alone — a different shape again from Revenue Rescue (branching saga) and DataOpsBench
S21 (parallel merge/verify): a straight chain gated before the one irreversible, side-effecting step.

    rdo mission validate examples/deploy_release/mission.py
    rdo mission run      examples/deploy_release/mission.py --approve
    rdo mission bundle   examples/deploy_release/mission.py --out /tmp/release.json
    rdo mission replay   examples/deploy_release/mission.py /tmp/release.json
"""
from __future__ import annotations

from redevops_mission import MissionProgram, Operator, capability, step, template


@template("deploy_release")
def deploy_release(mission_id):
    return [
        step("artifact_built", need="build the release artifact from the tagged commit"),
        step("tests_passed", need="run the release test suite against the artifact",
             after=["artifact_built"]),
        step("release_published", need="publish the release to the registry",
             after=["tests_passed"],
             constraints=["irreversible publish — requires human approval"]),
        step("release_announced", need="announce the release to the changelog and subscribers",
             after=["release_published"]),
    ]


OPERATORS = [
    Operator("ci-build", [
        capability("build.artifact", handler=lambda i: {"artifact": "app-1.4.0.tar"},
                   provides=["artifact_built"], permissions=["ci:build"]),
        capability("build.test", handler=lambda i: {"passed": 42, "failed": 0},
                   provides=["tests_passed"], permissions=["ci:test"]),
    ]),
    Operator("release", [
        capability("release.publish", handler=lambda i: {"version": "1.4.0", "url": "registry/app/1.4.0"},
                   provides=["release_published"], side_effecting=True, approval_required=True,
                   undo="release.yank", permissions=["release:publish"], estimated_value="high"),
        capability("release.announce", handler=lambda i: {"announced": True},
                   provides=["release_announced"], side_effecting=True, permissions=["release:announce"]),
    ]),
]

GRANTS = ["ci:build", "ci:test", "release:publish", "release:announce"]

PROGRAM = MissionProgram.from_template(
    "deploy_release", goal="Cut and publish release 1.4.0", grants=GRANTS,
)
