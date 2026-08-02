"""One compilation path — a compiler-emitted mission (design §13.3).

This fixture demonstrates the seam Quantify (a domain compiler) and the Discovery Runtime both use: an
upstream source emits a `MissionProposal`, which becomes a `MissionProgram` compiled and operated
**identically** to a hand-authored one — `validate` / `run` / `replay` / `ci` don't care where it came
from. Here `compile_scenario` stands in for Quantify's strategy compiler (real Quantify emits the same
shape from a natural-language scenario); the same pattern applies to a Discovery proposal.

    rdo mission validate examples/from_proposal/mission.py
    rdo mission ci       examples/from_proposal/mission.py
"""
from __future__ import annotations

from redevops_mission import (
    MissionProgram, MissionProposal, MissionStep, Operator, capability,
)


# ---- the "compiler" (stand-in for Quantify's strategy compiler) --------------------------------------
def compile_scenario(scenario: dict) -> MissionProposal:
    """Map a structured financial scenario to a source-agnostic MissionProposal. Real Quantify does this
    from a natural-language strategy; the emitted shape — and everything downstream — is the same."""
    strategy = scenario["strategy"]
    return MissionProposal(
        name="backtest_scenario",
        goal=f"Backtest and record: {strategy}",
        source="compiler:quantify",
        grants=["market:read", "sim:run", "research:write"],
        steps=[
            MissionStep(outcome="market_data_loaded",
                        need=f"load {scenario['universe']} market data for the backtest window"),
            MissionStep(outcome="portfolio_simulated",
                        need=f"simulate the {strategy} strategy over the window",
                        after=["market_data_loaded"]),
            MissionStep(outcome="metrics_computed",
                        need="compute TWR / MWR and risk metrics from the simulation",
                        after=["portfolio_simulated"]),
            MissionStep(outcome="worksheet_saved",
                        need="save an immutable research worksheet revision",
                        after=["metrics_computed"],
                        constraints=["persists a research record — requires human confirmation"]),
        ],
    )


SCENARIO = {"strategy": "60/40 stocks-bonds, annual rebalance", "universe": "US total market + aggregate bond"}

# the one public artifact — compiled from a proposal, then identical to any hand-authored program
PROGRAM = MissionProgram.from_proposal(compile_scenario(SCENARIO))


OPERATORS = [
    Operator("quantify-market", [
        capability("market.load", handler=lambda i: {"rows": 12000},
                   provides=["market_data_loaded"], permissions=["market:read"]),
    ]),
    Operator("quantify-sim", [
        capability("sim.run", handler=lambda i: {"nav_curve": "…"},
                   provides=["portfolio_simulated"], permissions=["sim:run"]),
        capability("sim.metrics", handler=lambda i: {"twr": 0.071, "mwr": 0.068, "maxdd": -0.34},
                   provides=["metrics_computed"], permissions=["sim:run"]),
    ]),
    Operator("quantify-research", [
        capability("research.save_worksheet", handler=lambda i: {"revision": "ws_1"},
                   provides=["worksheet_saved"], side_effecting=True, approval_required=True,
                   undo="research.delete_revision", permissions=["research:write"]),
    ]),
]
