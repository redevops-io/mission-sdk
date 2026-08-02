"""Graph-shape metrics for `rdo mission profile` — derived from the compiled plan, no execution."""
from __future__ import annotations


def _levels(nodes) -> dict[str, int]:
    """Longest-path level of each node (roots = 1); the level count is the critical-path depth."""
    by_id = {n.id: n for n in nodes}
    memo: dict[str, int] = {}

    def level(nid: str) -> int:
        if nid in memo:
            return memo[nid]
        node = by_id[nid]
        memo[nid] = 1 + max((level(d) for d in node.depends_on if d in by_id), default=0)
        return memo[nid]

    return {n.id: level(n.id) for n in nodes}


def topology(plan) -> dict:
    nodes = plan.graph.nodes
    lv = _levels(nodes)
    per_level = [list(lv.values()).count(l) for l in set(lv.values())]
    side = [n for n in nodes if n.side_effecting]
    return {
        "nodes": len(nodes),
        "edges": sum(len(n.depends_on) for n in nodes),
        "critical_path_depth": max(lv.values(), default=0),
        "max_parallelism": max(per_level, default=0),
        "merge_points": sum(1 for n in nodes if len(n.depends_on) > 1),
        "human_gates": sum(1 for n in nodes if n.approval_required),
        "side_effecting": len(side),
        "undo_covered": sum(1 for n in side if n.undo),
    }
