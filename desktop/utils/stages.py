"""Stage machine shared by desktop + web (keep in sync)."""

STANDARD_FLOW = ["Created", "PR", "PO", "GRN", "SentToFinance", "Paid"]
STRAIGHT_FLOW = ["Created", "SentToFinance", "Paid"]

def flow_for(inv_type: str) -> list[str]:
    return STANDARD_FLOW if inv_type == "standard" else STRAIGHT_FLOW

def next_stage(inv_type: str, current: str) -> str | None:
    flow = flow_for(inv_type)
    try:
        i = flow.index(current)
    except ValueError:
        return None
    return flow[i + 1] if i + 1 < len(flow) else None

def can_transition(inv_type: str, from_stage: str, to_stage: str) -> bool:
    """Only exact forward-one-step moves are legal. Admin revert handled separately."""
    return next_stage(inv_type, from_stage) == to_stage
