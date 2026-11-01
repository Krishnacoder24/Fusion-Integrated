from django.urls import path

from modules.elm.api.views import (
    MyLeaveApplicationsView,
    WithdrawLeaveApplicationView,
    LeaveDecisionView,
)
urlpatterns = [
    path(
        "applications",
        MyLeaveApplicationsView.as_view(),
        name="elm-my-applications",
    ),
    path(
        "applications/<int:pk>/withdraw",
        WithdrawLeaveApplicationView.as_view(),
        name="elm-withdraw-application",
    ),
    path(
        "applications/<int:pk>/decision",
        LeaveDecisionView.as_view(),
        name="elm-leave-decision",
    ),
]