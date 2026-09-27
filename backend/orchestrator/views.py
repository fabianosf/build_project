from django.http import StreamingHttpResponse

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from orchestrator.services.attachment_service import enrich_request_text
from orchestrator.services.catalog_service import (
    health_payload,
    list_fragments_grouped,
    resync_catalog,
)
from orchestrator.services.discovery_service import sync_discovered
from orchestrator.services.llm.base import (
    LLMError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMTimeoutError,
)
from orchestrator.services.llm.factory import get_llm_provider
from orchestrator.services.orchestration_service import (
    OrchestrationError,
    continue_chat,
    forge_draft,
    iter_chat_sse,
    run_specialist,
)
from orchestrator.services.sandbox_service import SandboxError, run_python
from orchestrator.services.selection_service import suggest_specialists
from orchestrator.services.workspace_service import (
    WorkspaceError,
    apply_patches,
    list_dir_prefixes as workspace_list_dirs,
    list_tree as workspace_list_tree,
    read_file as workspace_read_file,
    search_files as workspace_search_files,
    status as workspace_status,
)
from orchestrator.services.workspace_run_service import run_recipe as workspace_run_recipe


def _context_paths_from(data: dict) -> list[str]:
    raw = data.get("context_paths") or data.get("workspace_paths") or []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        path = item.strip().replace("\\", "/")
        if not path or path in seen:
            continue
        seen.add(path)
        out.append(path)
        if len(out) >= 12:
            break
    return out

def _fragment_id_from(data: dict) -> str:
    return (
        data.get("fragment_id")
        or data.get("specialist_id")
        or data.get("especialista_id")
        or ""
    ).strip()


def _request_text_from(data: dict) -> str:
    return (data.get("request") or data.get("pedido") or "").strip()


def _map_llm_error(exc: LLMError) -> Response:
    if isinstance(exc, LLMTimeoutError):
        return Response(
            {
                "error": str(exc),
                "code": "timeout",
                "retryable": True,
            },
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    if isinstance(exc, LLMProviderError):
        http_status = getattr(exc, "http_status", status.HTTP_502_BAD_GATEWAY)
        return Response(
            {
                "error": str(exc),
                "code": getattr(exc, "code", "provider_error"),
                "retryable": bool(getattr(exc, "retryable", False)),
            },
            status=http_status,
        )
    if isinstance(exc, LLMInvalidResponseError):
        return Response(
            {
                "error": str(exc),
                "code": "invalid_response",
                "retryable": True,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response(
        {"error": str(exc), "code": "llm_error", "retryable": True},
        status=status.HTTP_502_BAD_GATEWAY,
    )


class HealthView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        payload = health_payload()
        code = (
            status.HTTP_200_OK
            if payload["fragments_ok"]
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=code)


class FragmentsView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        payload = list_fragments_grouped()
        if payload["missing"]:
            return Response(
                {
                    **payload,
                    "error": (
                        "Arquivos do catálogo ausentes em fragmentos/: "
                        + ", ".join(payload["missing"])
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(payload)


class SuggestView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        text = _request_text_from(request.data)
        attachments = request.data.get("attachments") or []
        if attachments is not None and not isinstance(attachments, list):
            return Response(
                {"error": "Campo 'attachments' deve ser uma lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        enriched, attach_warnings, _imgs = enrich_request_text(text, attachments)
        if not enriched.strip():
            return Response(
                {
                    "error": "Informe um pedido ou anexe um arquivo "
                    "(.md, .txt, .pdf, .docx…)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = int(request.data.get("limit", 5))
        try:
            payload = suggest_specialists(
                enriched,
                limit=limit,
                provider=get_llm_provider(),
            )
            if attach_warnings:
                existing = payload.get("warning")
                joined = "; ".join(attach_warnings)
                payload["warning"] = (
                    f"{existing}; {joined}" if existing else joined
                )
                payload["attachment_warnings"] = attach_warnings
            return Response(payload)
        except Exception as exc:  # noqa: BLE001 — surface clean API errors
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ForgeView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        text = _request_text_from(request.data)
        fragment_id = _fragment_id_from(request.data)
        attachments = request.data.get("attachments") or []
        if not fragment_id:
            return Response(
                {"error": "Campo 'fragment_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if attachments is not None and not isinstance(attachments, list):
            return Response(
                {"error": "Campo 'attachments' deve ser uma lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not text and not attachments:
            return Response(
                {
                    "error": "Informe um pedido ou anexe um arquivo "
                    "(.md, .txt, .pdf, .docx…)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sync_discovered()
            result = forge_draft(
                text,
                fragment_id,
                get_llm_provider(),
                attachments=attachments,
            )
        except OrchestrationError as exc:
            return Response({"error": str(exc)}, status=exc.http_status)
        except LLMError as exc:
            return _map_llm_error(exc)
        return Response(result)


class RunPipelineView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        text = _request_text_from(request.data)
        fragment_id = _fragment_id_from(request.data)
        approved_draft = (request.data.get("approved_draft") or "").strip()

        if not text or not fragment_id or not approved_draft:
            return Response(
                {
                    "error": (
                        "Campos 'request', 'fragment_id' e 'approved_draft' "
                        "são obrigatórios."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sync_discovered()
            result = run_specialist(
                text,
                fragment_id,
                approved_draft,
                get_llm_provider(),
            )
        except OrchestrationError as exc:
            return Response({"error": str(exc)}, status=exc.http_status)
        except LLMError as exc:
            return _map_llm_error(exc)

        return Response(result)


class ChatView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        fragment_id = _fragment_id_from(request.data)
        message = (request.data.get("message") or request.data.get("content") or "").strip()
        history = request.data.get("history") or []
        attachments = request.data.get("attachments") or []
        activation = bool(request.data.get("activation") or request.data.get("document_recognized"))
        web_search = bool(request.data.get("web_search"))
        suggest_diff = bool(
            request.data.get("suggest_diff") or request.data.get("suggest_diffs")
        )
        use_workspace = bool(
            request.data.get("use_workspace") or request.data.get("workspace")
        )
        include_git = bool(
            request.data.get("include_git") or request.data.get("git_context")
        )
        agent_tools = bool(
            request.data.get("agent_tools") or request.data.get("agent")
        )
        context_paths = _context_paths_from(request.data)

        if not fragment_id:
            return Response(
                {"error": "Campo 'fragment_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(history, list):
            return Response(
                {"error": "Campo 'history' deve ser uma lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(attachments, list):
            return Response(
                {"error": "Campo 'attachments' deve ser uma lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sync_discovered()
            result = continue_chat(
                fragment_id,
                message,
                history,
                attachments,
                get_llm_provider(),
                activation=activation,
                web_search=web_search,
                suggest_diff=suggest_diff,
                use_workspace=use_workspace,
                include_git=include_git,
                agent_tools=agent_tools,
                context_paths=context_paths,
            )
        except OrchestrationError as exc:
            return Response({"error": str(exc)}, status=exc.http_status)
        except LLMError as exc:
            return _map_llm_error(exc)

        return Response(result)


class ChatStreamView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> StreamingHttpResponse | Response:
        fragment_id = _fragment_id_from(request.data)
        message = (
            request.data.get("message") or request.data.get("content") or ""
        ).strip()
        history = request.data.get("history") or []
        attachments = request.data.get("attachments") or []
        activation = bool(
            request.data.get("activation")
            or request.data.get("document_recognized")
        )
        web_search = bool(request.data.get("web_search"))
        suggest_diff = bool(
            request.data.get("suggest_diff") or request.data.get("suggest_diffs")
        )
        use_workspace = bool(
            request.data.get("use_workspace") or request.data.get("workspace")
        )
        include_git = bool(
            request.data.get("include_git") or request.data.get("git_context")
        )
        agent_tools = bool(
            request.data.get("agent_tools") or request.data.get("agent")
        )
        context_paths = _context_paths_from(request.data)

        if not fragment_id:
            return Response(
                {"error": "Campo 'fragment_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(history, list) or not isinstance(attachments, list):
            return Response(
                {"error": "history e attachments devem ser listas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sync_discovered()
        stream = iter_chat_sse(
            fragment_id,
            message,
            history,
            attachments,
            get_llm_provider(),
            activation=activation,
            web_search=web_search,
            suggest_diff=suggest_diff,
            use_workspace=use_workspace,
            include_git=include_git,
            agent_tools=agent_tools,
            context_paths=context_paths,
        )
        response = StreamingHttpResponse(
            stream,
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class CatalogResyncView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        payload = resync_catalog()
        return Response(payload)


class SandboxPythonView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        code = request.data.get("code")
        if not isinstance(code, str):
            return Response(
                {"error": "Campo 'code' (string) é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = run_python(code)
        except SandboxError as exc:
            return Response(
                {"error": str(exc), "ok": False},
                status=exc.http_status,
            )
        return Response(result)


class WorkspaceStatusView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        return Response(workspace_status())


class WorkspaceFileView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        rel = (request.query_params.get("path") or "").strip()
        if not rel:
            return Response(
                {"error": "Query 'path' é obrigatória."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(workspace_read_file(rel))
        except WorkspaceError as exc:
            return Response(
                {"error": str(exc)},
                status=exc.http_status,
            )


class WorkspaceSearchView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        q = (request.query_params.get("q") or "").strip()
        try:
            dirs = workspace_list_dirs(query=q, limit=16)
            dir_hits = [
                {
                    "path": f"{d}/",
                    "score": 50.0,
                    "snippet": "pasta",
                    "kind": "dir",
                }
                for d in dirs
            ]
            if not q:
                paths = workspace_list_tree(limit=40)
                file_hits = [
                    {
                        "path": p,
                        "score": 0.0,
                        "snippet": "",
                        "kind": "file",
                    }
                    for p in paths
                ]
            else:
                file_hits = [
                    {**h, "kind": "file"} for h in workspace_search_files(q)
                ]
            # Prefer matching folders first for @pasta UX
            hits = dir_hits + file_hits
        except WorkspaceError as exc:
            return Response(
                {"error": str(exc)},
                status=exc.http_status,
            )
        return Response({"query": q, "results": hits[:40]})


class WorkspaceTreeView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        prefix = (request.query_params.get("prefix") or "").strip().strip("/")
        try:
            files = workspace_list_tree(limit=200)
            dirs = workspace_list_dirs(query=prefix, limit=80)
        except WorkspaceError as exc:
            return Response(
                {"error": str(exc)},
                status=exc.http_status,
            )
        if prefix:
            pref = prefix + "/"
            files = [p for p in files if p.startswith(pref)]
            dirs = [d for d in dirs if d == prefix or d.startswith(pref)]
        entries = (
            [{"path": f"{d}/", "kind": "dir"} for d in dirs[:60]]
            + [{"path": p, "kind": "file"} for p in files[:120]]
        )
        return Response({"prefix": prefix, "entries": entries})


class WorkspaceApplyDiffView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        patches = request.data.get("patches")
        if not isinstance(patches, list) or not patches:
            return Response(
                {"error": "Campo 'patches' (lista não vazia) é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = apply_patches(patches)
        except WorkspaceError as exc:
            return Response(
                {"error": str(exc), "ok": False},
                status=exc.http_status,
            )
        return Response(result)


class WorkspaceRunView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        recipe = (
            request.data.get("recipe")
            or request.data.get("command")
            or ""
        )
        if not isinstance(recipe, str) or not recipe.strip():
            return Response(
                {
                    "error": (
                        "Campo 'recipe' é obrigatório "
                        "(ex.: pytest, manage_test, npm_build)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = workspace_run_recipe(recipe.strip())
        except WorkspaceError as exc:
            return Response(
                {"error": str(exc), "ok": False},
                status=exc.http_status,
            )
        return Response(result)
