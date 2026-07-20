"""
SDLC state definition shared by all agent nodes and Celery tasks.
"""
from typing import TypedDict, Optional, List


class SDLCState(TypedDict):
    # Run identifiers
    run_id: str
    project_id: str
    ticket_id: Optional[str]
    pod_id: str

    # Raw data loaded from DB (serializable dicts)
    project: dict         # Project fields
    ticket: dict          # Ticket fields
    pod_agents: List[dict]  # list of {agent_id, agent_role, execution_order}

    # Agent outputs
    sprint_plan: Optional[str]
    branch_name: Optional[str]
    pr_url: Optional[str]
    pr_number: Optional[int]
    test_results: Optional[dict]

    # Flow control
    current_agent: str
    dev_retries: int
    max_dev_retries: int
    errors: List[str]
    status: str           # queued | running | awaiting_approval | failed | completed


def initial_state(
    run_id: str,
    project: dict,
    ticket: dict,
    pod_agents: List[dict],
    max_dev_retries: int = 2,
) -> SDLCState:
    return SDLCState(
        run_id=run_id,
        project_id=str(project["id"]),
        ticket_id=str(ticket["id"]) if ticket.get("id") else None,
        pod_id=str(project.get("pod_id", "")),
        project=project,
        ticket=ticket,
        pod_agents=pod_agents,
        sprint_plan=None,
        branch_name=None,
        pr_url=None,
        pr_number=None,
        test_results=None,
        current_agent="sprint",
        dev_retries=0,
        max_dev_retries=max_dev_retries,
        errors=[],
        status="running",
    )
