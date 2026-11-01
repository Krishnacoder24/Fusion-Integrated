"""API views for Employee Leave Management."""


from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404

from modules.elm.domain.state_machine import InvalidLeaveTransition
from modules.elm.services.applications import process_leave_action

from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError

from fusion_auth.permissions import (
    HasModuleGrant,
    HasPermission,
    IsAuthenticatedPrincipal,
)
from modules.elm.models import LeaveApplication




class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "leave_type",
            "start_date",
            "end_date",
            "requested_days",
            "reason",
            "half_day_period",
            "status",
            "substitute_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        requested_days = attrs.get(
            "requested_days",
            getattr(self.instance, "requested_days", None),
        )
        half_day_period = attrs.get(
            "half_day_period",
            getattr(self.instance, "half_day_period", None),
        )

        if start_date and end_date and end_date < start_date:
            raise ValidationError({
                "end_date": "End date cannot be earlier than start date."
            })

        if half_day_period:
            if start_date != end_date:
                raise ValidationError({
                    "half_day_period": (
                        "Half-day leave must be requested for a single day."
                    )
                })

            if requested_days != Decimal("0.5"):
                raise ValidationError({
                    "requested_days": (
                        "Half-day leave must have a duration of 0.5 days."
                    )
                })

        return attrs


class MyLeaveApplicationsView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            action_permission = HasPermission("elm.application.view_self")
        else:
            action_permission = HasPermission("elm.application.create")

        return [
            IsAuthenticatedPrincipal(),
            HasModuleGrant("elm"),
            action_permission(),
        ]

    def get_queryset(self):
        principal = self.request.principal
        return LeaveApplication.objects.filter(user_id=principal.user_id)

    def perform_create(self, serializer):
        principal = self.request.principal
        serializer.save(user_id=principal.user_id)






class WithdrawLeaveApplicationView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("elm"),
        HasPermission("elm.application.withdraw"),
    ]

    def post(self, request, pk):
        principal = request.principal

        with transaction.atomic():
            try:
                application = (
                    LeaveApplication.objects
                    .select_for_update()
                    .get(pk=pk, user_id=principal.user_id)
                )
            except LeaveApplication.DoesNotExist:
                return Response(
                    {"detail": "Leave application not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            withdrawable_statuses = {
                "submitted",
                "pending_substitute",
                "pending_unit_head",
                "pending_sanction",
                "recommended",
            }

            if application.status not in withdrawable_statuses:
                return Response(
                    {
                        "detail": (
                            "Only leave applications awaiting final approval "
                            "can be withdrawn."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            application.status = "withdrawn"
            application.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "id": application.pk,
                "status": application.status,
                "detail": "Leave application withdrawn.",
            },
            status=status.HTTP_200_OK,
        )




class LeaveDecisionView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("elm"),
    ]

    def post(self, request, pk):
        action = request.data.get("action")
        note = request.data.get("note", "")

        if action not in {"approve", "reject", "recommend", "not_recommend"}:
            return Response(
                {"detail": "Invalid decision action."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Recommendations require review permission.
        # Final decisions require sanction permission.
        if action in {"recommend", "not_recommend"}:
            permission = HasPermission("elm.application.review")
        else:
            permission = HasPermission("elm.application.sanction")

        permission_instance = permission()
        if not permission_instance.has_permission(request, self):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        principal = request.principal

        try:
            application = process_leave_action(
                application_id=pk,
                actor_user_id=principal.user_id,
                action=action,
                note=note,
            )
        except LeaveApplication.DoesNotExist:
            raise Http404("Leave application not found.")
        except InvalidLeaveTransition as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": application.pk,
                "status": application.status,
                "decision_user_id": application.decision_user_id,
                "decision_at": application.decision_at,
                "decision_note": application.decision_note,
            },
            status=status.HTTP_200_OK,
        )