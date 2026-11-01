from django.db import transaction
from django.utils import timezone

from modules.elm.domain.state_machine import transition_leave
from modules.elm.models import LeaveApplication


@transaction.atomic
def process_leave_action(*, application_id, actor_user_id, action, note=""):
    application = (
        LeaveApplication.objects.select_for_update()
        .get(pk=application_id)
    )

    next_status = transition_leave(
        current_status=application.status,
        action=action,
        leave_type=application.leave_type,
    )

    application.status = next_status
    application.decision_user_id = actor_user_id
    application.decision_at = timezone.now()
    application.decision_note = note

    application.save(
        update_fields=[
            "status",
            "decision_user_id",
            "decision_at",
            "decision_note",
            "updated_at",
        ]
    )

    return application