"""Revenue Rescue — the first SDK fixture (dogfood test #1).

Recover a failed/late customer payment across billing → support → lifecycle → books. This is the
agentic-os PR #2 mission, re-authored through **only** the public SDK surface — no `agentic_os.*`
imports — to prove the boundary. Dunning is the money-moving step, so it carries the human gate; the
proactive reach-out and win-back run in parallel once dunning is approved; the books adjustment folds
them back in.

    rdo mission validate examples/revenue_rescue/mission.py
    rdo mission explain  examples/revenue_rescue/mission.py
"""
from __future__ import annotations

from redevops_mission import MissionProgram, Operator, capability, step, template


# ---- the mission: outcomes + their dependency shape --------------------------------------------------
@template("revenue_rescue")
def revenue_rescue(mission_id):
    return [
        step("dunning_attempted",
             need="chase the overdue invoice and retry the failed payment (dunning)",
             constraints=["money-moving — requires human approval"]),
        step("reply_drafted",
             need="proactively reach out to the customer about the failed payment",
             after=["dunning_attempted"]),
        step("campaign_drafted",
             need="compose a win-back lifecycle campaign for the at-risk customer",
             after=["dunning_attempted"]),
        step("reconciliation_staged",
             need="reconcile and adjust the books once the payment is recovered",
             after=["reply_drafted", "campaign_drafted"]),
    ]


# ---- the capabilities that provide those outcomes (the authored fleet) -------------------------------
# Handlers are stubs — validate/explain never run them; they exist so the operators are runnable later.
OPERATORS = [
    Operator("agentic-billing", [
        capability("billing.dunning", handler=lambda i: {"dunned": True},
                   provides=["dunning_attempted"], side_effecting=True, approval_required=True,
                   undo="billing.reverse_dunning", permissions=["billing:write"], estimated_value="high"),
    ]),
    Operator("agentic-support", [
        capability("support.draft_reply", handler=lambda i: {"draft": "…"},
                   provides=["reply_drafted"], permissions=["support:write"]),
    ]),
    Operator("agentic-lifecycle", [
        capability("lifecycle.compose_campaign", handler=lambda i: {"campaign": "winback"},
                   provides=["campaign_drafted"], permissions=["lifecycle:write"]),
    ]),
    Operator("agentic-books", [
        capability("books.reconcile", handler=lambda i: {"entry": "je_99"},
                   provides=["reconciliation_staged"], side_effecting=True,
                   undo="books.reverse_entry", permissions=["books:write"]),
    ]),
]

GRANTS = ["billing:write", "support:write", "lifecycle:write", "books:write"]

# ---- the one public artifact -------------------------------------------------------------------------
PROGRAM = MissionProgram.from_template(
    "revenue_rescue", goal="Recover a failed customer payment", grants=GRANTS,
)
