export type Prerequisite = {
  code: string;
  message: string;
};

export type Fragment = {
  id: string;
  filename: string;
  name: string;
  function: string;
  description?: string;
  category: string;
  is_prompt_forger: boolean;
  selectable_as_specialist: boolean;
  file_present: boolean;
  prerequisites?: Prerequisite[];
  auto_discovered?: boolean;
};

export type CategoryGroup = {
  name: string;
  fragments: Fragment[];
};

export type FragmentsResponse = {
  catalog_version: string;
  missing: string[];
  categories: CategoryGroup[];
  discovered_new?: string[];
  auto_count?: number;
  error?: string;
};

export type Suggestion = {
  id: string;
  name: string;
  category: string;
  description: string;
  score: number;
  matched_terms: string[];
  explanation: string;
  prerequisites: Prerequisite[];
  filename: string;
  is_prompt_forger: boolean;
};

export type ProjectSniff = {
  stacks: string[];
  project_kind: string;
  confidence: number;
  reasons: string[];
  error_kind?: string | null;
  is_debug?: boolean;
  auto_activate_recommended?: boolean;
  summary?: string;
};

export type SuggestResponse = {
  request: string;
  intents_detected: string[];
  stacks_detected: string[];
  prompt_creation_intent: boolean;
  suggestions: Suggestion[];
  mode?: "deterministic" | "hybrid";
  ai_interpreted?: boolean;
  interpretation?: {
    goal: string;
    ambiguities: string[];
    clarifying_question: string | null;
  } | null;
  attachment_warnings?: string[];
  warning?: string | null;
  project_sniff?: ProjectSniff | null;
  auto_pick?: string | null;
  auto_activate_recommended?: boolean;
  error?: string;
};

export type ActivationInfo = {
  detected: boolean;
  keys_found?: boolean;
  fragment_id: string;
  name: string;
  filename: string;
  content_sha256: string;
  activation_hash: string | null;
  identification_hashes: string[];
  commands: string[];
  notes: string;
};

export type ForgeResponse = {
  draft: string;
  request: string;
  fragment_id: string;
  fragment_name: string;
  mode: "preview" | "llm" | "activation";
  ai_executed: boolean;
  warning?: string;
  attachment_warnings?: string[];
  activation?: ActivationInfo | null;
  error?: string;
};

export type RunResponse = {
  response: string;
  fragment_id: string;
  fragment_name: string;
  status: string;
  mode: "preview" | "llm";
  ai_executed: boolean;
  warning?: string;
  request?: string;
  activation?: ActivationInfo | null;
  document_recognized?: boolean;
  fragment_truncated?: boolean;
  rag_used?: boolean;
  rag_chunks?: number;
  error?: string;
};

export type ChatAttachment = {
  name: string;
  mime: string;
  text?: string;
  data_base64?: string;
};

export type ChatHistoryTurn = {
  role: "user" | "assistant";
  content: string;
};

export type ChatResponse = {
  response: string;
  fragment_id: string;
  fragment_name: string;
  status: string;
  mode: "preview" | "llm";
  ai_executed: boolean;
  warning?: string | null;
  attachment_warnings?: string[];
  activation?: ActivationInfo | null;
  document_recognized?: boolean;
  fragment_truncated?: boolean;
  rag_used?: boolean;
  rag_chunks?: number;
  web_search_used?: boolean;
  web_search_provider?: string | null;
  web_search_results?: number;
  suggest_diff?: boolean;
  error?: string;
};

const API_BASE = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";

export type ApiErrorInfo = {
  message: string;
  code?: string;
  retryable?: boolean;
  status?: number;
};

export class ApiError extends Error {
  code?: string;
  retryable: boolean;
  status?: number;

  constructor(info: ApiErrorInfo) {
    super(info.message);
    this.name = "ApiError";
    this.code = info.code;
    this.retryable = Boolean(info.retryable);
    this.status = info.status;
  }
}

export function isRetryableError(err: unknown): boolean {
  if (err instanceof ApiError) return err.retryable;
  const msg = err instanceof Error ? err.message : String(err);
  return /429|413|rate|crédito|credito|timeout|tente de novo|prompt grande/i.test(
    msg,
  );
}

export function formatLlmError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "rate_limited" || err.status === 429) {
      return err.message;
    }
    if (err.code === "prompt_too_large" || err.status === 413) {
      return err.message;
    }
    return err.message;
  }
  return err instanceof Error ? err.message : String(err);
}

export type HealthResponse = {
  status: string;
  catalog_version: string;
  fragments_ok: boolean;
  llm_configured: boolean;
  llm?: {
    configured: boolean;
    model: string | null;
    base_host: string | null;
    approx_chars_per_token: number;
    note: string;
  };
  web_search?: {
    enabled: boolean;
    brave_configured: boolean;
    max_results: number;
  };
  workspace?: {
    enabled: boolean;
    root_name: string | null;
    approx_files?: number;
    configured?: boolean;
    missing?: boolean;
    run_recipes?: WorkspaceRecipe[];
  };
  error?: string;
};

export type WorkspaceRecipe = {
  id: string;
  label: string;
  ready: boolean;
  reason?: string | null;
  argv?: string[];
  group?: "verify" | "git" | string;
};

export type TurnUsage = {
  prompt_chars?: number;
  completion_chars?: number;
  prompt_tokens_approx?: number;
  completion_tokens_approx?: number;
};

async function parseJson<T extends { error?: string; code?: string; retryable?: boolean }>(
  response: Response,
): Promise<T> {
  const data = (await response.json()) as T;
  if (!response.ok) {
    throw new ApiError({
      message: data.error ?? `Falha na API (HTTP ${response.status}).`,
      code: data.code,
      retryable:
        data.retryable ??
        (response.status === 429 ||
          response.status === 413 ||
          response.status === 504),
      status: response.status,
    });
  }
  return data;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/api/health/`);
  return parseJson<HealthResponse>(response);
}

export async function fetchFragments(): Promise<FragmentsResponse> {
  const response = await fetch(`${API_BASE}/api/fragments/`);
  return parseJson<FragmentsResponse>(response);
}

export async function resyncCatalog(): Promise<FragmentsResponse & {
  added?: string[];
  discovered_count?: number;
}> {
  const response = await fetch(`${API_BASE}/api/catalog/resync/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  return parseJson(response);
}

export async function suggestFragments(
  request: string,
  attachments: ChatAttachment[] = [],
): Promise<SuggestResponse> {
  const response = await fetch(`${API_BASE}/api/suggest/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request, attachments }),
  });
  return parseJson<SuggestResponse>(response);
}

export async function forgeDraft(
  request: string,
  fragmentId: string,
  attachments: ChatAttachment[] = [],
): Promise<ForgeResponse> {
  const response = await fetch(`${API_BASE}/api/forge/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request,
      fragment_id: fragmentId,
      attachments,
    }),
  });
  return parseJson<ForgeResponse>(response);
}

export async function runSpecialist(
  request: string,
  fragmentId: string,
  approvedDraft: string,
): Promise<RunResponse> {
  const response = await fetch(`${API_BASE}/api/run/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request,
      fragment_id: fragmentId,
      approved_draft: approvedDraft,
    }),
  });
  return parseJson<RunResponse>(response);
}

export async function chatContinue(params: {
  fragmentId: string;
  message: string;
  history: ChatHistoryTurn[];
  attachments: ChatAttachment[];
  activation: boolean;
  webSearch?: boolean;
  suggestDiff?: boolean;
  useWorkspace?: boolean;
  includeGit?: boolean;
  agentTools?: boolean;
  contextPaths?: string[];
}): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      fragment_id: params.fragmentId,
      message: params.message,
      history: params.history,
      attachments: params.attachments,
      activation: params.activation,
      web_search: Boolean(params.webSearch),
      suggest_diff: Boolean(params.suggestDiff),
      use_workspace: Boolean(params.useWorkspace),
      include_git: Boolean(params.includeGit),
      agent_tools: Boolean(params.agentTools),
      context_paths: params.contextPaths ?? [],
    }),
  });
  return parseJson<ChatResponse>(response);
}

export type ToolTraceStep = {
  round?: number;
  name: string;
  arguments?: Record<string, unknown>;
  ok?: boolean;
  error?: string | null;
  preview?: string;
};

export type ChatStreamHandlers = {
  onMeta?: (meta: {
    fragment_id: string;
    fragment_name: string;
    fragment_truncated?: boolean;
    rag_used?: boolean;
    rag_chunks?: number;
    web_search_used?: boolean;
    web_search_provider?: string | null;
    web_search_results?: number;
    workspace_used?: boolean;
    workspace_files?: number;
    git_included?: boolean;
    agent_tools?: boolean;
    suggest_diff?: boolean;
    warning?: string | null;
    document_recognized?: boolean;
    usage?: TurnUsage;
  }) => void;
  onTool?: (step: ToolTraceStep) => void;
  onToken?: (text: string) => void;
  onDone?: (payload: {
    response: string;
    ai_executed: boolean;
    mode: string;
    usage?: TurnUsage;
    tool_trace?: ToolTraceStep[];
  }) => void;
  onError?: (error: string, info?: { code?: string; retryable?: boolean }) => void;
};

export async function chatContinueStream(
  params: {
    fragmentId: string;
    message: string;
    history: ChatHistoryTurn[];
    attachments: ChatAttachment[];
    activation: boolean;
    webSearch?: boolean;
    suggestDiff?: boolean;
    useWorkspace?: boolean;
    includeGit?: boolean;
    agentTools?: boolean;
    contextPaths?: string[];
  },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/chat/stream/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fragment_id: params.fragmentId,
        message: params.message,
        history: params.history,
        attachments: params.attachments,
        activation: params.activation,
        web_search: Boolean(params.webSearch),
        suggest_diff: Boolean(params.suggestDiff),
        use_workspace: Boolean(params.useWorkspace),
        include_git: Boolean(params.includeGit),
        agent_tools: Boolean(params.agentTools),
        context_paths: params.contextPaths ?? [],
      }),
      signal,
    });
  } catch (err) {
    if (signal?.aborted || (err instanceof DOMException && err.name === "AbortError")) {
      handlers.onError?.("Geração interrompida.", {
        code: "aborted",
        retryable: false,
      });
      return;
    }
    throw err;
  }
  if (!response.ok || !response.body) {
    let err = `Falha no stream (HTTP ${response.status}).`;
    let code: string | undefined;
    let retryable =
      response.status === 429 ||
      response.status === 413 ||
      response.status === 504;
    try {
      const data = (await response.json()) as {
        error?: string;
        code?: string;
        retryable?: boolean;
      };
      if (data.error) err = data.error;
      code = data.code;
      if (typeof data.retryable === "boolean") retryable = data.retryable;
    } catch {
      /* ignore */
    }
    handlers.onError?.(err, { code, retryable });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel();
        handlers.onError?.("Geração interrompida.", {
          code: "aborted",
          retryable: false,
        });
        return;
      }
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const block of parts) {
        const line = block
          .split("\n")
          .map((l) => l.trim())
          .find((l) => l.startsWith("data:"));
        if (!line) continue;
        const raw = line.replace(/^data:\s?/, "");
        try {
          const evt = JSON.parse(raw) as {
            type: string;
            text?: string;
            error?: string;
            code?: string;
            retryable?: boolean;
            response?: string;
            ai_executed?: boolean;
            mode?: string;
            fragment_id?: string;
            fragment_name?: string;
            fragment_truncated?: boolean;
            rag_used?: boolean;
            rag_chunks?: number;
            warning?: string | null;
            document_recognized?: boolean;
            usage?: TurnUsage;
            tool_trace?: ToolTraceStep[];
            name?: string;
            round?: number;
            arguments?: Record<string, unknown>;
            ok?: boolean;
            preview?: string;
            agent_tools?: boolean;
          };
          if (evt.type === "meta") {
            handlers.onMeta?.({
              fragment_id: evt.fragment_id ?? "",
              fragment_name: evt.fragment_name ?? "",
              fragment_truncated: evt.fragment_truncated,
              rag_used: evt.rag_used,
              rag_chunks: evt.rag_chunks,
              warning: evt.warning,
              document_recognized: evt.document_recognized,
              agent_tools: evt.agent_tools,
              usage: evt.usage,
            });
          } else if (evt.type === "tool" && evt.name) {
            handlers.onTool?.({
              round: evt.round,
              name: evt.name,
              arguments: evt.arguments,
              ok: evt.ok,
              error: evt.error,
              preview: evt.preview,
            });
          } else if (evt.type === "token" && evt.text) {
            handlers.onToken?.(evt.text);
          } else if (evt.type === "done") {
            handlers.onDone?.({
              response: evt.response ?? "",
              ai_executed: Boolean(evt.ai_executed),
              mode: evt.mode ?? "llm",
              usage: evt.usage,
              tool_trace: evt.tool_trace,
            });
          } else if (evt.type === "error") {
            handlers.onError?.(evt.error ?? "Erro no stream.", {
              code: evt.code,
              retryable: evt.retryable,
            });
          }
        } catch {
          /* skip bad chunk */
        }
      }
    }
  } catch (err) {
    if (signal?.aborted || (err instanceof DOMException && err.name === "AbortError")) {
      handlers.onError?.("Geração interrompida.", {
        code: "aborted",
        retryable: false,
      });
      return;
    }
    throw err;
  }
}

export type WorkspaceSearchHit = {
  path: string;
  score?: number;
  snippet?: string;
  kind?: "file" | "dir";
};

export async function searchWorkspaceFiles(
  query = "",
): Promise<WorkspaceSearchHit[]> {
  const q = encodeURIComponent(query);
  const response = await fetch(`${API_BASE}/api/workspace/search/?q=${q}`);
  const data = await parseJson<{
    results?: WorkspaceSearchHit[];
    error?: string;
  }>(response);
  return data.results ?? [];
}

export type WorkspaceTreeEntry = {
  path: string;
  kind: "file" | "dir";
};

export async function fetchWorkspaceTree(
  prefix = "",
): Promise<WorkspaceTreeEntry[]> {
  const q = encodeURIComponent(prefix);
  const response = await fetch(
    `${API_BASE}/api/workspace/tree/?prefix=${q}`,
  );
  const data = await parseJson<{
    entries?: WorkspaceTreeEntry[];
    error?: string;
  }>(response);
  return data.entries ?? [];
}

export type WorkspaceFilePayload = {
  path: string;
  content: string;
  chars?: number;
  truncated?: boolean;
  error?: string;
};

export async function readWorkspaceFile(
  path: string,
): Promise<WorkspaceFilePayload> {
  const q = encodeURIComponent(path);
  const response = await fetch(`${API_BASE}/api/workspace/file/?path=${q}`);
  return parseJson<WorkspaceFilePayload>(response);
}

export type SandboxResult = {
  ok: boolean;
  stdout: string;
  stderr: string;
  timed_out?: boolean;
  error?: string | null;
  exit_code?: number | null;
};

export async function runSandboxPython(code: string): Promise<SandboxResult> {
  const response = await fetch(`${API_BASE}/api/sandbox/python/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  const data = (await response.json()) as SandboxResult & { error?: string };
  if (!response.ok) {
    throw new Error(data.error ?? `Sandbox falhou (HTTP ${response.status}).`);
  }
  return data;
}

export type ApplyDiffPatch = {
  path: string;
  unified_diff: string;
};

export type ApplyDiffResult = {
  applied: number;
  failed: number;
  results: Array<{
    path?: string;
    ok?: boolean;
    error?: string;
    backup?: string | null;
    created?: boolean;
  }>;
  error?: string;
};

export async function applyWorkspaceDiffs(
  patches: ApplyDiffPatch[],
): Promise<ApplyDiffResult> {
  const response = await fetch(`${API_BASE}/api/workspace/apply-diff/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patches }),
  });
  return parseJson<ApplyDiffResult>(response);
}

export type WorkspaceRunResult = {
  ok: boolean;
  recipe: string;
  label: string;
  argv: string[];
  cwd: string;
  exit_code: number;
  timed_out: boolean;
  stdout: string;
  stderr: string;
  combined: string;
  error?: string;
};

export async function runWorkspaceRecipe(
  recipe: string,
): Promise<WorkspaceRunResult> {
  const response = await fetch(`${API_BASE}/api/workspace/run/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recipe }),
  });
  return parseJson<WorkspaceRunResult>(response);
}
