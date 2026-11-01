"""Domain state machine for Employee Leave Management."""

from dataclasses import dataclass


@dataclass
class InvalidLeaveTransition(Exception):
    """Raised when a leave application transition is not permitted."""

    current_status: str
    action: str
    detail: str

    def __str__(self):
        return self.detail


# CL and RH are decided by the Unit Head.
UNIT_HEAD_FINAL_LEAVE_TYPES = {"CL", "RH"}

# These leave types require a recommendation stage followed by sanction.
HIERARCHICAL_LEAVE_TYPES = {"SCL", "EL", "COL", "VL"}

# Actions accepted by the state machine.
ACTIONS = {
    "route_to_unit_head",
    "request_substitute",
    "substitute_confirmed",
    "approve",
    "reject",
    "recommend",
    "not_recommend",
    "withdraw",
}


def transition_leave(
    *,
    current_status: str,
    action: str,
    leave_type: str,
) -> str:
    """Return the next status for a valid leave workflow transition.

    This function validates domain transitions only. It does not verify
    whether the requesting user has permission to perform the action.
    """
    if action not in ACTIONS:
        raise InvalidLeaveTransition(
            current_status,
            action,
            f"Unknown leave workflow action: {action}",
        )

    if current_status in {"approved", "rejected", "withdrawn", "cancelled"}:
        raise InvalidLeaveTransition(
            current_status,
            action,
            f"Applications in '{current_status}' status cannot use this workflow.",
        )

    if leave_type not in UNIT_HEAD_FINAL_LEAVE_TYPES | HIERARCHICAL_LEAVE_TYPES:
        raise InvalidLeaveTransition(
            current_status,
            action,
            f"Unsupported leave type: {leave_type}",
        )

    # An employee's request starts in submitted status.
    if current_status == "submitted":
        if action == "route_to_unit_head":
            return "pending_unit_head"
        if action == "request_substitute":
            return "pending_substitute"

    # Substitute confirmation sends the request to the Unit Head.
    if current_status == "pending_substitute":
        if action == "substitute_confirmed":
            return "pending_unit_head"

    # Unit Head makes the final decision for CL and RH.
    if current_status == "pending_unit_head":
        if leave_type in UNIT_HEAD_FINAL_LEAVE_TYPES:
            if action == "approve":
                return "approved"
            if action == "reject":
                return "rejected"

        # For hierarchical leave types, the Unit Head recommends or
        # does not recommend; neither decision is the final sanction.
        if leave_type in HIERARCHICAL_LEAVE_TYPES:
            if action in {"recommend", "not_recommend"}:
                return "pending_sanction"

    # Final sanctioning authority decides hierarchical leave requests.
    if current_status == "pending_sanction":
        if leave_type in HIERARCHICAL_LEAVE_TYPES:
            if action == "approve":
                return "approved"
            if action == "reject":
                return "rejected"

    # Withdrawal is available before final approval or rejection.
    if action == "withdraw" and current_status in {
        "submitted",
        "pending_substitute",
        "pending_unit_head",
        "pending_sanction",
        "recommended",
    }:
        return "withdrawn"

    raise InvalidLeaveTransition(
        current_status,
        action,
        (
            f"Action '{action}' is not allowed from status "
            f"'{current_status}' for leave type '{leave_type}'."
        ),
    )