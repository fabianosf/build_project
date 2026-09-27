from django.urls import path

from orchestrator.views import (
    CatalogResyncView,
    ChatStreamView,
    ChatView,
    ForgeView,
    FragmentsView,
    HealthView,
    RunPipelineView,
    SandboxPythonView,
    SuggestView,
    WorkspaceApplyDiffView,
    WorkspaceFileView,
    WorkspaceRunView,
    WorkspaceSearchView,
    WorkspaceStatusView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("fragments/", FragmentsView.as_view(), name="fragments"),
    path("catalog/resync/", CatalogResyncView.as_view(), name="catalog-resync"),
    path("suggest/", SuggestView.as_view(), name="suggest"),
    path("forge/", ForgeView.as_view(), name="forge"),
    path("run/", RunPipelineView.as_view(), name="run"),
    path("chat/", ChatView.as_view(), name="chat"),
    path("chat/stream/", ChatStreamView.as_view(), name="chat-stream"),
    path("sandbox/python/", SandboxPythonView.as_view(), name="sandbox-python"),
    path("workspace/", WorkspaceStatusView.as_view(), name="workspace-status"),
    path("workspace/file/", WorkspaceFileView.as_view(), name="workspace-file"),
    path("workspace/search/", WorkspaceSearchView.as_view(), name="workspace-search"),
    path(
        "workspace/apply-diff/",
        WorkspaceApplyDiffView.as_view(),
        name="workspace-apply-diff",
    ),
    path("workspace/run/", WorkspaceRunView.as_view(), name="workspace-run"),
]
