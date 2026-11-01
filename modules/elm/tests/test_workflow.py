import pytest

from modules.elm.domain.state_machine import (
    InvalidLeaveTransition,
    transition_leave,
)


@pytest.mark.parametrize("leave_type", ["CL", "RH"])
def test_unit_head_can_approve_casual_and_restricted_holiday_leave(leave_type):
    assert transition_leave(
        current_status="pending_unit_head",
        action="approve",
        leave_type=leave_type,
    ) == "approved"


@pytest.mark.parametrize("leave_type", ["CL", "RH"])
def test_unit_head_can_reject_casual_and_restricted_holiday_leave(leave_type):
    assert transition_leave(
        current_status="pending_unit_head",
        action="reject",
        leave_type=leave_type,
    ) == "rejected"


@pytest.mark.parametrize("leave_type", ["SCL", "EL", "COL", "VL"])
@pytest.mark.parametrize("action", ["recommend", "not_recommend"])
def test_unit_head_decisions_continue_to_final_sanction(leave_type, action):
    assert transition_leave(
        current_status="pending_unit_head",
        action=action,
        leave_type=leave_type,
    ) == "pending_sanction"


@pytest.mark.parametrize("leave_type", ["SCL", "EL", "COL", "VL"])
@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        ("approve", "approved"),
        ("reject", "rejected"),
    ],
)
def test_final_sanctioning_decision(leave_type, action, expected_status):
    assert transition_leave(
        current_status="pending_sanction",
        action=action,
        leave_type=leave_type,
    ) == expected_status


def test_substitute_confirmation_routes_to_unit_head():
    assert transition_leave(
        current_status="pending_substitute",
        action="substitute_confirmed",
        leave_type="EL",
    ) == "pending_unit_head"


def test_withdrawal_is_allowed_before_final_decision():
    assert transition_leave(
        current_status="pending_sanction",
        action="withdraw",
        leave_type="EL",
    ) == "withdrawn"


@pytest.mark.parametrize(
    "current_status",
    ["approved", "rejected", "withdrawn", "cancelled"],
)
def test_terminal_status_cannot_be_approved_again(current_status):
    with pytest.raises(InvalidLeaveTransition):
        transition_leave(
            current_status=current_status,
            action="approve",
            leave_type="CL",
        )


def test_unit_head_cannot_finally_approve_earned_leave():
    with pytest.raises(InvalidLeaveTransition):
        transition_leave(
            current_status="pending_unit_head",
            action="approve",
            leave_type="EL",
        )


def test_unknown_action_is_rejected():
    with pytest.raises(InvalidLeaveTransition):
        transition_leave(
            current_status="submitted",
            action="do_something",
            leave_type="CL",
        )