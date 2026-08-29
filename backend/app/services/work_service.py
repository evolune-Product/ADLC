"""
Work service — the valid-transition enforcement for the generic Work entity.

Kept out of the router the same way `policy_service` is kept out of
`runs.py`: the status machine is a pure function of (current, target) that a
test can exercise with zero DB, and the router's only job is to call it and
turn a bad transition into a 409.
"""
from app.models.work import VALID_TRANSITIONS, WORK_STATUSES


class InvalidTransition(Exception):
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Cannot move work item from '{current}' to '{target}'")


def assert_valid_status(status: str) -> None:
    if status not in WORK_STATUSES:
        raise ValueError(f"Unknown work status: {status}")


def can_transition(current: str, target: str) -> bool:
    if current == target:
        return True
    return target in VALID_TRANSITIONS.get(current, ())


def apply_transition(current: str, target: str) -> str:
    """Returns the new status or raises InvalidTransition."""
    assert_valid_status(target)
    if not can_transition(current, target):
        raise InvalidTransition(current, target)
    return target
