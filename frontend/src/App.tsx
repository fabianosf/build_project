import { FormEvent, useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import {
  fetchFragments,
  fetchHealth,
  forgeDraft,
  chatContinueStream,
  formatLlmError,
  isRetryableError,
  resyncCatalog,
  runSandboxPython,
  runSpecialist,
  runWorkspaceRecipe,
  searchWorkspaceFiles,
  suggestFragments,
  type CategoryGroup,
  type ChatAttachment,
  type ChatHistoryTurn,
  type Fragment,
  type FragmentsResponse,
  type ForgeResponse,
  type HealthResponse,
  type ProjectSniff,
  type RunResponse,
  type Suggestion,
  type ActivationInfo,
  type TurnUsage,
  type WorkspaceRecipe,
  type ToolTraceStep,
  type WorkspaceSearchHit,
} from "./api";
import {
  clearSessions,
  deleteSession,
  downloadText,
  exportFilename,
  listSessions,
  saveSession,
  sessionToJson,
  sessionToMarkdown,
  turnCountLabel,
  type RunSession,
  type SessionTurn,
} from "./historyStore";
import { FOLDER_MAX_FILES, pickFolderFiles } from "./folderPicker";
import { parseDiffBlocks } from "./diffBlocks";
import { DiffPanel } from "./DiffPanel";
import { WorkspacePanel } from "./WorkspacePanel";
import { REQUEST_EXAMPLES } from "./requestExamples";
import { buildCommitSuggestion } from "./commitSuggest";

type Phase = "select" | "review" | "result";
type UiStep = 1 | 2 | 3;

const UI_STEPS = [
  { id: 1 as const, label: "Pedido" },
  { id: 2 as const, label: "Especialista" },
  { id: 3 as const, label: "Resposta" },
];

function FragmentCard({
  fragment,
  selected,
  onSelect,
  disabled,
}: {
  fragment: Fragment;
  selected: boolean;
  onSelect: (id: string) => void;
  disabled?: boolean;
}) {
  const {
    id,
    name,
    function: role,
    category,
    filename,
    is_prompt_forger,
    auto_discovered,
  } = fragment;

  return (
    <article
      className={`card${selected ? " card-selected" : ""}${
        disabled ? " card-disabled" : ""
      }`}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-pressed={selected}
      aria-disabled={disabled}
      onClick={() => {
        if (!disabled) onSelect(id);
      }}
      onKeyDown={(e) => {
        if (disabled) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(id);
        }
      }}
    >
      <header className="card-header">
        <h3>{name}</h3>
        {is_prompt_forger ? (
          <span className="badge">Prompt Forger</span>
        ) : null}
        {auto_discovered ? <span className="badge badge-auto">Auto</span> : null}
        {selected ? <span className="badge badge-selected">Selecionado</span> : null}
      </header>
      <p className="card-function">{role}</p>
      <dl className="card-meta">
        <div>
          <dt>Categoria</dt>
          <dd>{category}</dd>
        </div>
        <div>
          <dt>Arquivo</dt>
          <dd>
            <code>{filename}</code>
          </dd>
        </div>
      </dl>
    </article>
  );
}

function findFragment(
  data: FragmentsResponse | null,
  id: string | null,
): Fragment | null {
  if (!data || !id) return null;
  for (const section of data.categories) {
    const hit = section.fragments.find((f) => f.id === id);
    if (hit) return hit;
  }
  return null;
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export default function App() {
  const [data, setData] = useState<FragmentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [requestText, setRequestText] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [suggestMeta, setSuggestMeta] = useState<{
    intents: string[];
    stacks: string[];
    mode: "deterministic" | "hybrid";
    aiInterpreted: boolean;
    warning: string | null;
    interpretation: {
      goal: string;
      ambiguities: string[];
      clarifying_question: string | null;
    } | null;
    projectSniff: ProjectSniff | null;
    autoPick: string | null;
    autoActivateRecommended: boolean;
  } | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [phase, setPhase] = useState<Phase>("select");
  const [draft, setDraft] = useState("");
  const [draftEditable, setDraftEditable] = useState(false);
  const [forgeInfo, setForgeInfo] = useState<ForgeResponse | null>(null);
  const [pipelineBusy, setPipelineBusy] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<RunResponse | null>(null);
  const [copyNotice, setCopyNotice] = useState<string | null>(null);
  const [resyncing, setResyncing] = useState(false);
  const [discoveredBanner, setDiscoveredBanner] = useState<string[] | null>(
    null,
  );
  const [history, setHistory] = useState<RunSession[]>(() => listSessions());
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activationInfo, setActivationInfo] = useState<ActivationInfo | null>(
    null,
  );
  const [activatedDoc, setActivatedDoc] = useState<{
    name: string;
    filename: string;
    hash: string | null;
  } | null>(null);

  const [chatMessages, setChatMessages] = useState<ChatHistoryTurn[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatTyping, setChatTyping] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [pendingAttachments, setPendingAttachments] = useState<
    (ChatAttachment & { id: string })[]
  >([]);
  const [chatWarning, setChatWarning] = useState<string | null>(null);
  const [fragmentTruncated, setFragmentTruncated] = useState(false);
  const [ragInfo, setRagInfo] = useState<{ used: boolean; chunks: number }>({
    used: false,
    chunks: 0,
  });
  const [sandboxBusy, setSandboxBusy] = useState(false);
  const [lastSandboxOut, setLastSandboxOut] = useState<string | null>(null);
  const [verifyBusy, setVerifyBusy] = useState(false);
  const [lastVerifyOut, setLastVerifyOut] = useState<string | null>(null);
  const [runRecipes, setRunRecipes] = useState<WorkspaceRecipe[]>([]);
  const [llmHealth, setLlmHealth] = useState<HealthResponse["llm"] | null>(
    null,
  );
  const [webSearchMeta, setWebSearchMeta] = useState<
    HealthResponse["web_search"] | null
  >(null);
  const [workspaceMeta, setWorkspaceMeta] = useState<
    HealthResponse["workspace"] | null
  >(null);
  const [lastUsage, setLastUsage] = useState<TurnUsage | null>(null);
  const [chatRetryable, setChatRetryable] = useState(false);
  const [pipelineRetryable, setPipelineRetryable] = useState(false);
  const [webSearchOn, setWebSearchOn] = useState(false);
  const [useWorkspaceOn, setUseWorkspaceOn] = useState(false);
  const [includeGitOn, setIncludeGitOn] = useState(false);
  const [agentToolsOn, setAgentToolsOn] = useState(false);
  const [toolSteps, setToolSteps] = useState<ToolTraceStep[]>([]);
  const [suggestDiffOn, setSuggestDiffOn] = useState(false);
  const [folderHint, setFolderHint] = useState<string | null>(null);
  const [contextPaths, setContextPaths] = useState<string[]>([]);
  const [atHits, setAtHits] = useState<WorkspaceSearchHit[]>([]);
  const [atOpen, setAtOpen] = useState(false);
  const [postApplyVerify, setPostApplyVerify] = useState(false);
  const [commitSuggestBusy, setCommitSuggestBusy] = useState(false);

  const [showHistory, setShowHistory] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showCatalog, setShowCatalog] = useState(false);
  const [catalogFilter, setCatalogFilter] = useState("");

  const draftRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatAbortRef = useRef<AbortController | null>(null);
  const atSearchTimer = useRef<number | null>(null);

  function refreshHistory() {
    setHistory(listSessions());
  }

  function persistProject(messages: SessionTurn[], opts?: {
    response?: string;
    runMode?: "preview" | "llm";
    aiExecuted?: boolean;
    attachmentNames?: string[];
    documentRecognized?: boolean;
  }) {
    if (!selectedId) return null;
    const frag = findFragment(data, selectedId);
    const lastAssistant = [...messages]
      .reverse()
      .find((m) => m.role === "assistant");
    const prevNames =
      (activeSessionId
        ? history.find((s) => s.id === activeSessionId)?.attachmentNames
        : undefined) ?? [];
    const mergedNames = Array.from(
      new Set([
        ...prevNames,
        ...(opts?.attachmentNames ?? []),
      ]),
    );
    const saved = saveSession({
      id: activeSessionId ?? undefined,
      request: requestText.trim() || messages.find((m) => m.role === "user")?.content || "",
      selectedId,
      fragmentName:
        runResult?.fragment_name ||
        forgeInfo?.fragment_name ||
        frag?.name ||
        selectedId,
      fragmentFilename: frag?.filename ?? "",
      suggestMode: suggestMeta?.mode ?? null,
      intents: suggestMeta?.intents ?? [],
      stacks: suggestMeta?.stacks ?? [],
      interpretationGoal: suggestMeta?.interpretation?.goal ?? null,
      draft: draft.trim(),
      response: opts?.response ?? lastAssistant?.content ?? runResult?.response ?? "",
      runMode: opts?.runMode ?? runResult?.mode ?? "llm",
      aiExecuted: opts?.aiExecuted ?? runResult?.ai_executed ?? true,
      messages,
      attachmentNames: mergedNames,
      documentRecognized:
        opts?.documentRecognized ??
        Boolean(activatedDoc || runResult?.document_recognized),
    });
    setActiveSessionId(saved.id);
    refreshHistory();
    return saved;
  }

  async function loadCatalog() {
    const payload = await fetchFragments();
    setData(payload);
    setError(null);
    if (payload.discovered_new?.length) {
      setDiscoveredBanner(payload.discovered_new);
    }
    return payload;
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [payload, health] = await Promise.all([
          fetchFragments(),
          fetchHealth().catch(() => null),
        ]);
        if (!cancelled) {
          setData(payload);
          setError(null);
          if (payload.discovered_new?.length) {
            setDiscoveredBanner(payload.discovered_new);
          }
          if (health?.llm) setLlmHealth(health.llm);
          if (health?.web_search) setWebSearchMeta(health.web_search);
          if (health?.workspace) {
            setWorkspaceMeta(health.workspace);
            if (health.workspace.enabled) setUseWorkspaceOn(true);
            setRunRecipes(health.workspace.run_recipes ?? []);
            const hasGit = (health.workspace.run_recipes ?? []).some(
              (r) => r.group === "git" && r.ready,
            );
            if (hasGit) setIncludeGitOn(true);
            if (health.workspace.enabled) setAgentToolsOn(true);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(formatLlmError(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleResync() {
    setResyncing(true);
    setError(null);
    try {
      const payload = await resyncCatalog();
      await loadCatalog();
      if (payload.added?.length) {
        setDiscoveredBanner(payload.added);
      } else if (payload.discovered_new?.length) {
        setDiscoveredBanner(payload.discovered_new);
      } else {
        setDiscoveredBanner([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar catálogo");
    } finally {
      setResyncing(false);
    }
  }

  const selected = useMemo(
    () => findFragment(data, selectedId),
    [data, selectedId],
  );

  const selectedPrereqs = useMemo(() => {
    if (!selectedId) return [];
    const fromCatalog = selected?.prerequisites ?? [];
    const fromSuggest =
      suggestions?.find((s) => s.id === selectedId)?.prerequisites ?? [];
    return fromSuggest.length ? fromSuggest : fromCatalog;
  }, [selected, selectedId, suggestions]);

  const uiStep: UiStep = useMemo(() => {
    if (phase === "result" && runResult) return 3;
    if (phase === "review" || phase === "result") return 3;
    if (suggestions !== null) return 2;
    return 1;
  }, [phase, runResult, suggestions]);

  const lastAssistantMarkdown = useMemo(() => {
    const fromChat = [...chatMessages]
      .reverse()
      .find((m) => m.role === "assistant" && m.content.trim());
    if (fromChat) return fromChat.content;
    return runResult?.response ?? "";
  }, [chatMessages, runResult]);

  const suggestedDiffBlocks = useMemo(
    () => parseDiffBlocks(lastAssistantMarkdown),
    [lastAssistantMarkdown],
  );

  function applyRequestExample(id: string) {
    const ex = REQUEST_EXAMPLES.find((e) => e.id === id);
    if (!ex) return;
    setRequestText(ex.text);
    if (ex.suggestDiff) setSuggestDiffOn(true);
    if (ex.webSearch) setWebSearchOn(true);
    setSuggestError(null);
    if (ex.id === "folder-diffs") {
      setFolderHint(
        "Use «Pasta local» para anexar arquivos do projeto antes de Continuar.",
      );
    }
  }

  async function handleSuggest(event: FormEvent) {
    event.preventDefault();
    const text = requestText.trim();
    if (!text && pendingAttachments.length === 0) {
      setSuggestError("Digite o pedido ou anexe um arquivo.");
      return;
    }
    setSuggesting(true);
    setSuggestError(null);
    setShowCatalog(false);
    const attachments = pendingAttachments.map((a) => ({
      name: a.name,
      mime: a.mime,
      text: a.text,
      data_base64: a.data_base64,
    }));
    try {
      const result = await suggestFragments(text, attachments);
      setSuggestions(result.suggestions);
      setSuggestMeta({
        intents: result.intents_detected,
        stacks: result.stacks_detected,
        mode: result.mode ?? "deterministic",
        aiInterpreted: Boolean(result.ai_interpreted),
        warning: result.warning ?? null,
        interpretation: result.interpretation ?? null,
        projectSniff: result.project_sniff ?? null,
        autoPick: result.auto_pick ?? null,
        autoActivateRecommended: Boolean(result.auto_activate_recommended),
      });
      const pick = result.auto_pick || result.suggestions[0]?.id;
      if (pick) {
        setSelectedId(pick);
      }
      if (result.suggestions.length === 0) {
        setShowCatalog(true);
      }
    } catch (err) {
      setSuggestError(err instanceof Error ? err.message : "Erro ao sugerir");
      setSuggestions(null);
    } finally {
      setSuggesting(false);
    }
  }

  async function handleForge() {
    if (!selectedId) {
      setPipelineError("Escolha um especialista.");
      return;
    }
    if (!requestText.trim() && pendingAttachments.length === 0) {
      setPipelineError("Informe o pedido ou anexe um arquivo.");
      return;
    }
    setPipelineBusy(true);
    setPipelineError(null);
    setPipelineRetryable(false);
    setRunResult(null);
    setActivatedDoc(null);
    const attachments = pendingAttachments.map((a) => ({
      name: a.name,
      mime: a.mime,
      text: a.text,
      data_base64: a.data_base64,
    }));
    try {
      const result = await forgeDraft(
        requestText.trim(),
        selectedId,
        attachments,
      );
      setForgeInfo(result);
      setDraft(result.draft);
      setDraftEditable(false);
      setActivationInfo(result.activation ?? null);
      if (result.mode === "activation") {
        await openConversationAfterPrep(result);
      } else {
        setPhase("review");
      }
    } catch (err) {
      setPipelineError(formatLlmError(err));
      setPipelineRetryable(isRetryableError(err));
    } finally {
      setPipelineBusy(false);
    }
  }

  async function handleActivateAndHelp() {
    const pick = suggestMeta?.autoPick || selectedId;
    if (!pick) return;
    const name =
      suggestions?.find((s) => s.id === pick)?.name ||
      findFragment(data, pick)?.name ||
      pick;
    const base =
      requestText.trim() ||
      "Ajude a diagnosticar e corrigir o erro do projeto com base nos anexos.";
    const activationRequest = `Ativar ${name}. ${base}`;
    setSelectedId(pick);
    setRequestText(activationRequest);
    setPipelineBusy(true);
    setPipelineError(null);
    setRunResult(null);
    setActivatedDoc(null);
    const attachments = pendingAttachments.map((a) => ({
      name: a.name,
      mime: a.mime,
      text: a.text,
      data_base64: a.data_base64,
    }));
    try {
      const result = await forgeDraft(activationRequest, pick, attachments);
      setForgeInfo(result);
      setDraft(result.draft);
      setDraftEditable(false);
      setActivationInfo(result.activation ?? null);
      if (result.mode === "activation") {
        await openConversationAfterPrep(result);
      } else {
        setPhase("review");
      }
    } catch (err) {
      setPipelineError(
        formatLlmError(err) || "Erro ao ativar ajuda",
      );
      setPipelineRetryable(isRetryableError(err));
    } finally {
      setPipelineBusy(false);
    }
  }

  async function openConversationAfterPrep(forge: ForgeResponse) {
    if (!selectedId) return;
    setPipelineError(null);
    setChatBusy(true);
    setChatTyping(true);
    setToolSteps([]);
    chatAbortRef.current?.abort();
    const abort = new AbortController();
    chatAbortRef.current = abort;
    const userLine =
      requestText.trim() ||
      `(anexos: ${pendingAttachments.map((a) => a.name).join(", ")})`;
    const attachmentsPayload: ChatAttachment[] = pendingAttachments.map(
      (a) => ({
        name: a.name,
        mime: a.mime,
        text: a.text,
        data_base64: a.data_base64,
      }),
    );
    setChatMessages([
      { role: "user", content: userLine },
      { role: "assistant", content: "" },
    ]);
    setPhase("result");
    setDraft(forge.draft);
    try {
      let gotToken = false;
      await chatContinueStream(
        {
          fragmentId: selectedId,
          message:
            "Confirme o reconhecimento/ativação deste documento (cite nome e hash se houver) e declare-se pronto. Em seguida analise o pedido e anexos do usuário; aguarde perguntas.",
          history: [],
          attachments: attachmentsPayload,
          activation: true,
          webSearch: webSearchOn,
          suggestDiff: suggestDiffOn,
          useWorkspace: useWorkspaceOn || contextPaths.length > 0,
          includeGit: includeGitOn,
          agentTools: agentToolsOn,
          contextPaths,
        },
        {
          onMeta: (meta) => {
            setFragmentTruncated(Boolean(meta.fragment_truncated));
            setRagInfo({
              used: Boolean(meta.rag_used),
              chunks: meta.rag_chunks ?? 0,
            });
            if (meta.warning) setChatWarning(meta.warning);
            setActivatedDoc({
              name: meta.fragment_name,
              filename: "",
              hash: null,
            });
            setRunResult({
              response: "",
              fragment_id: meta.fragment_id,
              fragment_name: meta.fragment_name,
              status: "chatting",
              mode: "llm",
              ai_executed: true,
              request: userLine,
              document_recognized: true,
              fragment_truncated: meta.fragment_truncated,
              rag_used: meta.rag_used,
              rag_chunks: meta.rag_chunks,
              warning: meta.warning ?? undefined,
            });
          },
          onTool: (step) => {
            setToolSteps((prev) => [...prev, step]);
          },
          onToken: (text) => {
            if (!gotToken) {
              gotToken = true;
              setChatTyping(false);
            }
            setChatMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = {
                  role: "assistant",
                  content: last.content + text,
                };
              }
              return next;
            });
          },
          onDone: (payload) => {
            setChatTyping(false);
            if (payload.usage) setLastUsage(payload.usage);
            if (payload.tool_trace?.length) {
              setToolSteps(payload.tool_trace);
            }
            setChatMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = {
                  role: "assistant",
                  content: payload.response || last.content,
                };
              }
              persistProject(next, {
                response: payload.response,
                runMode: payload.mode as "preview" | "llm",
                aiExecuted: payload.ai_executed,
                attachmentNames: attachmentsPayload.map((a) => a.name),
                documentRecognized: true,
              });
              return next;
            });
            setRunResult((prev) =>
              prev
                ? {
                    ...prev,
                    response: payload.response,
                    ai_executed: payload.ai_executed,
                    mode: payload.mode as "preview" | "llm",
                    status: "chatting",
                  }
                : prev,
            );
            setActivatedDoc((prev) =>
              prev
                ? prev
                : {
                    name: forge.fragment_name,
                    filename: forge.activation?.filename ?? "",
                    hash: forge.activation?.activation_hash ?? null,
                  },
            );
            if (forge.activation) {
              setActivationInfo(forge.activation);
              setActivatedDoc({
                name: forge.activation.name,
                filename: forge.activation.filename,
                hash: forge.activation.activation_hash,
              });
            }
            setPendingAttachments([]);
          },
          onError: (error, info) => {
            setChatTyping(false);
            if (info?.code === "aborted") {
              setToolSteps([]);
              setCopyNotice("Geração interrompida.");
              window.setTimeout(() => setCopyNotice(null), 2500);
              return;
            }
            setPipelineError(error);
            setPipelineRetryable(Boolean(info?.retryable) || isRetryableError(error));
            setPhase("review");
          },
        },
        abort.signal,
      );
    } catch (err) {
      setChatTyping(false);
      if (abort.signal.aborted) {
        setToolSteps([]);
        return;
      }
      const msg = err instanceof Error ? err.message : "Erro ao iniciar conversa";
      setPipelineError(msg);
      setPhase("review");
    } finally {
      if (chatAbortRef.current === abort) chatAbortRef.current = null;
      setChatBusy(false);
      setChatTyping(false);
    }
  }

  function handleEditDraft() {
    setDraftEditable(true);
    queueMicrotask(() => draftRef.current?.focus());
  }

  function handleBackToSpecialist() {
    setPhase("select");
    setDraftEditable(false);
    setPipelineError(null);
    setRunResult(null);
    setForgeInfo(null);
    setDraft("");
    setActiveSessionId(null);
    setActivationInfo(null);
    setActivatedDoc(null);
    setChatMessages([]);
    setChatInput("");
    setPendingAttachments([]);
  }

  function handleNewRequest() {
    setPhase("select");
    setRequestText("");
    setSuggestions(null);
    setSuggestMeta(null);
    setSuggestError(null);
    setSelectedId(null);
    setDraft("");
    setDraftEditable(false);
    setForgeInfo(null);
    setRunResult(null);
    setPipelineError(null);
    setActiveSessionId(null);
    setActivationInfo(null);
    setActivatedDoc(null);
    setShowCatalog(false);
    setCatalogFilter("");
    setCopyNotice(null);
    setChatMessages([]);
    setChatInput("");
    setChatError(null);
    setContextPaths([]);
    setToolSteps([]);
    setPostApplyVerify(false);
    setAtOpen(false);
    setAtHits([]);
    chatAbortRef.current?.abort();
    chatAbortRef.current = null;
    setChatWarning(null);
    setPendingAttachments([]);
    setFragmentTruncated(false);
  }

  async function handleRun() {
    if (!selectedId || !draft.trim()) {
      setPipelineError("Revise o texto preparado antes de gerar a resposta.");
      return;
    }
    setPipelineBusy(true);
    setPipelineError(null);
    try {
      const result = await runSpecialist(
        requestText.trim(),
        selectedId,
        draft.trim(),
      );
      setRunResult(result);
      setPhase("result");
      setFragmentTruncated(Boolean(result.fragment_truncated));
      const frag = findFragment(data, selectedId);
      if (result.activation) {
        setActivationInfo(result.activation);
      }
      if (result.document_recognized) {
        setActivatedDoc({
          name: result.fragment_name,
          filename: result.activation?.filename ?? frag?.filename ?? "",
          hash: result.activation?.activation_hash ?? null,
        });
      }
      const chatThread: SessionTurn[] = [
        { role: "user", content: requestText.trim() },
        { role: "assistant", content: result.response },
      ];
      setChatMessages(chatThread);
      persistProject(chatThread, {
        response: result.response,
        runMode: result.mode,
        aiExecuted: result.ai_executed,
        documentRecognized: Boolean(result.document_recognized),
      });
      setChatInput("");
      setChatError(null);
      setChatWarning(result.warning ?? null);
      setPendingAttachments([]);
    } catch (err) {
      setPipelineError(
        formatLlmError(err) || "Erro ao gerar resposta",
      );
      setPipelineRetryable(isRetryableError(err));
    } finally {
      setPipelineBusy(false);
    }
  }

  function handleReopenSession(session: RunSession) {
    setRequestText(session.request);
    setSelectedId(session.selectedId);
    setSuggestions([]);
    setSuggestMeta(
      session.suggestMode
        ? {
            intents: session.intents,
            stacks: session.stacks,
            mode: session.suggestMode,
            aiInterpreted: Boolean(session.interpretationGoal),
            warning: null,
            interpretation: session.interpretationGoal
              ? {
                  goal: session.interpretationGoal,
                  ambiguities: [],
                  clarifying_question: null,
                }
              : null,
            projectSniff: null,
            autoPick: session.selectedId,
            autoActivateRecommended: false,
          }
        : null,
    );
    setSuggestError(null);
    setDraft(session.draft);
    setDraftEditable(false);
    setForgeInfo({
      draft: session.draft,
      request: session.request,
      fragment_id: session.selectedId,
      fragment_name: session.fragmentName,
      mode: session.runMode,
      ai_executed: session.aiExecuted,
    });
    setRunResult({
      response: session.response,
      fragment_id: session.selectedId,
      fragment_name: session.fragmentName,
      status: "from_history",
      mode: session.runMode,
      ai_executed: session.aiExecuted,
      request: session.request,
      document_recognized: session.documentRecognized,
    });
    setPhase("result");
    setPipelineError(null);
    setActiveSessionId(session.id);
    setShowHistory(false);
    setShowAdvanced(true);
    const thread =
      session.messages.length > 0
        ? session.messages
        : ([
            { role: "user", content: session.request },
            { role: "assistant", content: session.response },
          ] as SessionTurn[]);
    setChatMessages(thread);
    setChatInput("");
    setPendingAttachments([]);
    if (session.documentRecognized) {
      setActivatedDoc({
        name: session.fragmentName,
        filename: session.fragmentFilename,
        hash: null,
      });
    } else {
      setActivatedDoc(null);
    }
  }

  function handleClearHistory() {
    clearSessions();
    setHistory([]);
    setActiveSessionId(null);
  }

  function handleDeleteSession(id: string, event: MouseEvent) {
    event.stopPropagation();
    deleteSession(id);
    if (activeSessionId === id) setActiveSessionId(null);
    refreshHistory();
  }

  function handleExportSession(session: RunSession, format: "md" | "json") {
    if (format === "md") {
      downloadText(
        exportFilename(session, "md"),
        sessionToMarkdown(session),
        "text/markdown;charset=utf-8",
      );
    } else {
      downloadText(
        exportFilename(session, "json"),
        sessionToJson(session),
        "application/json;charset=utf-8",
      );
    }
  }

  function currentExportSession(): RunSession | null {
    if (activeSessionId) {
      const found = history.find((s) => s.id === activeSessionId);
      if (found) {
        return {
          ...found,
          messages:
            chatMessages.length > 0 ? chatMessages : found.messages,
          response:
            [...chatMessages].reverse().find((m) => m.role === "assistant")
              ?.content ?? found.response,
        };
      }
    }
    if (!runResult || !selectedId) return null;
    const messages: SessionTurn[] =
      chatMessages.length > 0
        ? chatMessages
        : [
            { role: "user", content: requestText.trim() },
            { role: "assistant", content: runResult.response },
          ];
    return {
      id: "current",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      title: requestText.trim().slice(0, 48) || runResult.fragment_name,
      request: requestText.trim(),
      selectedId,
      fragmentName: runResult.fragment_name,
      fragmentFilename: selected?.filename ?? "",
      suggestMode: suggestMeta?.mode ?? null,
      intents: suggestMeta?.intents ?? [],
      stacks: suggestMeta?.stacks ?? [],
      interpretationGoal: suggestMeta?.interpretation?.goal ?? null,
      draft: draft.trim(),
      response: runResult.response,
      runMode: runResult.mode,
      aiExecuted: runResult.ai_executed,
      messages,
      attachmentNames: [],
      documentRecognized: Boolean(
        activatedDoc || runResult.document_recognized,
      ),
    };
  }

  function handleExport(format: "md" | "json") {
    const session = currentExportSession();
    if (!session) return;
    handleExportSession(session, format);
  }

  async function handleCopy(which: "draft" | "response") {
    const lastAssistant = [...chatMessages]
      .reverse()
      .find((m) => m.role === "assistant");
    const text =
      which === "draft"
        ? draft
        : (lastAssistant?.content ?? runResult?.response ?? "");
    const ok = await copyText(text);
    setCopyNotice(
      ok
        ? `${which === "draft" ? "Texto" : "Resposta"} copiado.`
        : "Falha ao copiar.",
    );
    window.setTimeout(() => setCopyNotice(null), 2000);
  }

  async function readFileAsAttachment(
    file: File,
  ): Promise<ChatAttachment & { id: string }> {
    const id = `${file.name}-${file.size}-${file.lastModified}`;
    const mime = file.type || "application/octet-stream";
    const lower = file.name.toLowerCase();
    const isText =
      mime.startsWith("text/") ||
      mime === "application/json" ||
      /\.(txt|md|json|csv|py|ts|tsx|js|jsx|mjs|cjs|go|rs|java|kt|toml|ya?ml|css|scss|html|sql|sh|env\.example)$/i.test(
        lower,
      ) ||
      /\/(requirements\.txt|package\.json|dockerfile|manage\.py|settings\.py|go\.mod|cargo\.toml|tsconfig\.json|vite\.config\.(ts|js))$/i.test(
        lower,
      );

    if (isText) {
      const text = await file.text();
      return { id, name: file.name, mime: mime || "text/plain", text };
    }

    const buf = await file.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    const data_base64 = btoa(binary);
    return {
      id,
      name: file.name,
      mime: mime || "application/octet-stream",
      data_base64,
    };
  }

  async function handleFilesSelected(files: FileList | null) {
    if (!files?.length) return;
    const next: (ChatAttachment & { id: string })[] = [];
    for (const file of Array.from(files)) {
      if (file.size > 4 * 1024 * 1024) {
        const msg = `Arquivo grande demais (máx. 4 MB): ${file.name}`;
        setSuggestError(msg);
        setChatError(msg);
        continue;
      }
      try {
        next.push(await readFileAsAttachment(file));
      } catch {
        const msg = `Falha ao ler ${file.name}`;
        setSuggestError(msg);
        setChatError(msg);
      }
    }
    setPendingAttachments((prev) =>
      [...prev, ...next].slice(0, FOLDER_MAX_FILES),
    );
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleFolderSelected(files: FileList | null) {
    const picked = pickFolderFiles(files);
    if (!picked.files.length) {
      const msg =
        "Nenhum arquivo de código útil na pasta (ou todos filtrados).";
      setSuggestError(msg);
      setChatError(msg);
      if (folderInputRef.current) folderInputRef.current.value = "";
      return;
    }
    const next: (ChatAttachment & { id: string })[] = [];
    for (const file of picked.files) {
      try {
        next.push(await readFileAsAttachment(file));
      } catch {
        /* skip unreadable */
      }
    }
    setPendingAttachments((prev) =>
      [...prev, ...next].slice(0, FOLDER_MAX_FILES),
    );
    setSuggestDiffOn(true);
    const parts = [
      `Pasta «${picked.rootLabel}»: ${next.length} arquivo(s)`,
    ];
    if (picked.truncated) parts.push(`limitado a ${FOLDER_MAX_FILES}`);
    if (picked.skipped) parts.push(`${picked.skipped} ignorado(s)`);
    setFolderHint(parts.join(" · "));
    if (!requestText.trim()) {
      setRequestText(
        "Analise os arquivos da pasta anexada e sugira diffs (unified) para corrigir ou melhorar. Não afirme ter aplicado nada no disco.",
      );
    }
    if (!chatInput.trim() && uiStep === 3) {
      setChatInput(
        "Analise os arquivos anexados e sugira diffs (unified). Não afirme ter aplicado no disco.",
      );
    }
    if (folderInputRef.current) folderInputRef.current.value = "";
  }

  async function handleChatSend(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || chatBusy) return;
    const text = chatInput.trim();
    if (!text && pendingAttachments.length === 0) {
      setChatError("Digite uma pergunta ou anexe um arquivo.");
      return;
    }
    setChatBusy(true);
    setChatTyping(true);
    setChatError(null);
    setChatRetryable(false);
    setChatWarning(null);
    setToolSteps([]);
    chatAbortRef.current?.abort();
    const abort = new AbortController();
    chatAbortRef.current = abort;
    const displayUser =
      text ||
      `(anexos: ${pendingAttachments.map((a) => a.name).join(", ")})`;
    const historyForApi = chatMessages.slice(-12);
    const attachmentsPayload: ChatAttachment[] = pendingAttachments.map(
      (a) => ({
        name: a.name,
        mime: a.mime,
        text: a.text,
        data_base64: a.data_base64,
      }),
    );
    const pathsForTurn = [...contextPaths];
    setChatMessages((prev) => [
      ...prev,
      { role: "user", content: displayUser },
      { role: "assistant", content: "" },
    ]);
    setChatInput("");
    setPendingAttachments([]);
    setAtOpen(false);
    setAtHits([]);
    try {
      let gotToken = false;
      await chatContinueStream(
        {
          fragmentId: selectedId,
          message: text,
          history: historyForApi,
          attachments: attachmentsPayload,
          activation: Boolean(
            activatedDoc ||
              runResult?.document_recognized ||
              activationInfo?.detected,
          ),
          webSearch: webSearchOn,
          suggestDiff: suggestDiffOn,
          useWorkspace: useWorkspaceOn || pathsForTurn.length > 0,
          includeGit: includeGitOn,
          agentTools: agentToolsOn,
          contextPaths: pathsForTurn,
        },
        {
          onMeta: (meta) => {
            setFragmentTruncated(Boolean(meta.fragment_truncated));
            setRagInfo({
              used: Boolean(meta.rag_used),
              chunks: meta.rag_chunks ?? 0,
            });
            if (meta.warning) setChatWarning(meta.warning);
          },
          onTool: (step) => {
            setToolSteps((prev) => [...prev, step]);
          },
          onToken: (tok) => {
            if (!gotToken) {
              gotToken = true;
              setChatTyping(false);
            }
            setChatMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = {
                  role: "assistant",
                  content: last.content + tok,
                };
              }
              return next;
            });
          },
          onDone: (payload) => {
            setChatTyping(false);
            if (payload.usage) setLastUsage(payload.usage);
            if (payload.tool_trace?.length) {
              setToolSteps(payload.tool_trace);
            }
            setChatMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant" && payload.response) {
                next[next.length - 1] = {
                  role: "assistant",
                  content: payload.response,
                };
              }
              persistProject(next, {
                response: payload.response,
                runMode: payload.mode as "preview" | "llm",
                aiExecuted: payload.ai_executed,
                attachmentNames: attachmentsPayload.map((a) => a.name),
              });
              return next;
            });
            queueMicrotask(() =>
              chatEndRef.current?.scrollIntoView({ behavior: "smooth" }),
            );
          },
          onError: (error, info) => {
            setChatTyping(false);
            if (info?.code === "aborted") {
              setToolSteps([]);
              setCopyNotice("Geração interrompida.");
              window.setTimeout(() => setCopyNotice(null), 2500);
              return;
            }
            setChatError(error);
            setChatRetryable(Boolean(info?.retryable) || isRetryableError(error));
          },
        },
        abort.signal,
      );
    } catch (err) {
      setChatTyping(false);
      if (abort.signal.aborted) {
        setToolSteps([]);
      } else {
        setChatError(formatLlmError(err));
        setChatRetryable(isRetryableError(err));
      }
    } finally {
      if (chatAbortRef.current === abort) chatAbortRef.current = null;
      setChatBusy(false);
      setChatTyping(false);
    }
  }

  async function handleRunPython(code: string) {
    if (sandboxBusy) return;
    setSandboxBusy(true);
    setChatError(null);
    try {
      const result = await runSandboxPython(code);
      const out = result.ok
        ? result.stdout.trim() || "(sem saída)"
        : result.error || result.stderr || "Falha na execução";
      const body = result.ok
        ? `**Resultado do sandbox**\n\n\`\`\`\n${out}\n\`\`\``
        : `**Sandbox — erro**\n\n\`\`\`\n${out}\n\`\`\``;
      setLastSandboxOut(out);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: body },
      ]);
      queueMicrotask(() =>
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" }),
      );
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Erro no sandbox");
    } finally {
      setSandboxBusy(false);
    }
  }

  function sendSandboxToSpecialist() {
    if (!lastSandboxOut) return;
    setChatInput(
      (prev) =>
        `${prev ? `${prev}\n\n` : ""}Resultado da execução Python:\n\`\`\`\n${lastSandboxOut}\n\`\`\`\n`,
    );
  }

  function stopChatGeneration() {
    if (!chatAbortRef.current) return;
    chatAbortRef.current.abort();
    chatAbortRef.current = null;
    setToolSteps([]);
    setChatTyping(false);
    setChatBusy(false);
    setCopyNotice("Geração interrompida.");
    window.setTimeout(() => setCopyNotice(null), 2500);
  }

  function scheduleAtSearch(value: string) {
    if (!workspaceMeta?.enabled) {
      setAtOpen(false);
      setAtHits([]);
      return;
    }
    const match = /(^|\s)@([^\s@]*)$/.exec(value);
    if (!match) {
      setAtOpen(false);
      setAtHits([]);
      return;
    }
    const q = match[2] ?? "";
    setAtOpen(true);
    if (atSearchTimer.current != null) {
      window.clearTimeout(atSearchTimer.current);
    }
    atSearchTimer.current = window.setTimeout(() => {
      void searchWorkspaceFiles(q)
        .then((hits) => setAtHits(hits.slice(0, 12)))
        .catch(() => setAtHits([]));
    }, 180);
  }

  function pickContextPath(path: string) {
    const trimmed = path.trim().replace(/\\/g, "/");
    const normalized = trimmed.endsWith("/")
      ? `${trimmed.replace(/\/+$/, "")}/`
      : trimmed.replace(/\/+$/, "");
    if (!normalized) return;
    setContextPaths((prev) =>
      prev.includes(normalized) ? prev : [...prev, normalized].slice(0, 12),
    );
    setUseWorkspaceOn(true);
    setChatInput((prev) => prev.replace(/(^|\s)@[^\s@]*$/, "$1").trimEnd());
    setAtOpen(false);
    setAtHits([]);
  }

  async function handleSuggestCommit() {
    if (commitSuggestBusy || !workspaceMeta?.enabled) return;
    setCommitSuggestBusy(true);
    setChatError(null);
    try {
      const [statusRes, statRes] = await Promise.all([
        runWorkspaceRecipe("git_status"),
        runWorkspaceRecipe("git_diff_stat").catch(() => null),
      ]);
      const suggestion = buildCommitSuggestion(
        statusRes.combined || statusRes.stdout || "",
        statRes?.combined || statRes?.stdout || "",
      );
      setChatInput(suggestion);
      setCopyNotice("Mensagem de commit sugerida no composer (sem git commit).");
      window.setTimeout(() => setCopyNotice(null), 3500);
    } catch (err) {
      setChatError(
        err instanceof Error ? err.message : "Falha ao sugerir commit",
      );
    } finally {
      setCommitSuggestBusy(false);
    }
  }

  function preferredVerifyRecipe(): string | null {
    const ready = runRecipes.filter((r) => r.ready && r.group !== "git");
    const prefer = ["django_check", "manage_check", "pytest", "npm_test", "npm_build"];
    for (const id of prefer) {
      if (ready.some((r) => r.id === id)) return id;
    }
    return ready[0]?.id ?? null;
  }

  async function handleWorkspaceVerify(recipeId: string) {
    if (verifyBusy || chatBusy || !workspaceMeta?.enabled) return;
    setVerifyBusy(true);
    setChatError(null);
    setPostApplyVerify(false);
    try {
      const result = await runWorkspaceRecipe(recipeId);
      const combined = result.combined || result.stderr || result.stdout || "";
      setLastVerifyOut(combined);
      const statusLine = result.ok ? "ok" : "falhou";
      const body =
        `**Verificação (${result.label}) — ${statusLine}**\n\n` +
        `\`\`\`\n${combined}\n\`\`\``;
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: body },
      ]);
      setCopyNotice(
        result.ok
          ? `Verificação ${result.label}: ok`
          : `Verificação ${result.label}: exit ${result.exit_code}`,
      );
      window.setTimeout(() => setCopyNotice(null), 3000);
      queueMicrotask(() =>
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" }),
      );
    } catch (err) {
      setChatError(
        err instanceof Error ? err.message : "Falha na verificação",
      );
    } finally {
      setVerifyBusy(false);
    }
  }

  function sendVerifyToSpecialist() {
    if (!lastVerifyOut) return;
    setChatInput(
      (prev) =>
        `${prev ? `${prev}\n\n` : ""}Resultado da verificação do workspace:\n\`\`\`\n${lastVerifyOut}\n\`\`\`\nAnalise e sugira correções (diffs se necessário).`,
    );
    setSuggestDiffOn(true);
  }

  const mdComponents = {
    code({
      className,
      children,
    }: {
      className?: string;
      children?: ReactNode;
    }) {
      const text = String(children ?? "").replace(/\n$/, "");
      const lang = /language-(\w+)/.exec(className || "")?.[1];
      if (lang === "python") {
        return (
          <div className="code-run-block">
            <pre className="chat-md-pre">
              <code className={className}>{text}</code>
            </pre>
            <div className="code-run-actions">
              <button
                type="button"
                className="btn-secondary"
                disabled={sandboxBusy || chatBusy}
                onClick={() => void handleRunPython(text)}
              >
                {sandboxBusy ? "Executando…" : "Executar"}
              </button>
            </div>
          </div>
        );
      }
      if (className) {
        return (
          <pre className="chat-md-pre">
            <code className={className}>{text}</code>
          </pre>
        );
      }
      return <code className={className}>{children}</code>;
    },
    pre({ children }: { children?: ReactNode }) {
      return <>{children}</>;
    },
  };

  const fragmentCount = data
    ? data.categories.reduce((n, c) => n + c.fragments.length, 0)
    : 0;

  const filteredCategories = useMemo(() => {
    if (!data) return [];
    const q = catalogFilter.trim().toLowerCase();
    return data.categories
      .map((section) => ({
        ...section,
        fragments: section.fragments.filter((f) => {
          if (!q) return true;
          const hay = [
            f.name,
            f.id,
            f.filename,
            f.function,
            f.category,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
          return hay.includes(q);
        }),
      }))
      .filter((section) => section.fragments.length > 0);
  }, [data, catalogFilter]);

  function handleCatalogSelect(id: string) {
    setSelectedId(id);
    setSuggestError(null);
    setPipelineError(null);
  }

  return (
    <div className="page">
      <header className="hero">
        <div className="hero-top">
          <p className="eyebrow">Orquestrador</p>
          <div className="hero-top-right">
            {llmHealth ? (
              <span
                className={`llm-badge${llmHealth.configured ? " llm-ok" : " llm-off"}`}
                title={llmHealth.note}
              >
                {llmHealth.configured
                  ? `LLM · ${llmHealth.model ?? "?"}`
                  : "LLM · prévia"}
              </span>
            ) : null}
            <span
              className={`llm-badge${workspaceMeta?.enabled ? " llm-ok" : " llm-off"}`}
              title={
                workspaceMeta?.enabled
                  ? `WORKSPACE_ROOT ativo (${workspaceMeta.approx_files ?? "?"} arquivos)`
                  : "Defina WORKSPACE_ROOT no .env para ler/aplicar no disco"
              }
            >
              {workspaceMeta?.enabled
                ? `Workspace · ${workspaceMeta.root_name ?? "on"}`
                : "Workspace · off"}
            </span>
            <button
              type="button"
              className="btn-ghost"
              aria-expanded={showCatalog}
              aria-controls="catalog-drawer"
              onClick={() => setShowCatalog((v) => !v)}
              title="Listar todos os fragmentos/especialistas"
            >
              {showCatalog
                ? "Ocultar especialistas"
                : `Especialistas (${fragmentCount || "…"})`}
            </button>
            <button
              type="button"
              className="btn-ghost"
              aria-expanded={showAdvanced}
              onClick={() => setShowAdvanced((v) => !v)}
            >
              {showAdvanced ? "Fechar" : "Avançado"}
            </button>
          </div>
        </div>
        <h1>Orquestrador de Fragmentos</h1>
        <p className="lede">
          Descreva o que precisa; o app escolhe o especialista e gera a
          resposta.
        </p>
        {workspaceMeta && !workspaceMeta.enabled ? (
          <aside className="workspace-onboard" role="status">
            <strong>Workspace desligado.</strong> Para ler/aplicar diffs no
            disco, defina{" "}
            <code>WORKSPACE_ROOT=/caminho/absoluto/do/projeto</code> no{" "}
            <code>.env</code> e reinicie o backend.
          </aside>
        ) : null}
        {showAdvanced ? (
          <div className="advanced-box">
            <div className="form-actions hero-actions">
              <button
                type="button"
                className="btn-secondary"
                disabled={resyncing || loading}
                onClick={handleResync}
              >
                {resyncing ? "Atualizando…" : "Atualizar catálogo"}
              </button>
              {data ? (
                <span className="meta-line">
                  v{data.catalog_version} · {fragmentCount} especialistas
                  {typeof data.auto_count === "number"
                    ? ` · ${data.auto_count} auto`
                    : ""}
                </span>
              ) : null}
            </div>
            <button
              type="button"
              className="btn-link"
              onClick={() => setShowHistory((v) => !v)}
            >
              {showHistory
                ? "Ocultar projetos"
                : `Projetos (${history.length})`}
            </button>
          </div>
        ) : null}
      </header>

      {discoveredBanner && discoveredBanner.length > 0 ? (
        <p className="status warning" role="status">
          Novos fragmentos: {discoveredBanner.join(", ")}
        </p>
      ) : null}

      {showHistory ? (
        <section className="history-panel" aria-label="Projetos locais">
          <div className="section-head">
            <h2>Projetos</h2>
            <span className="count">{history.length}</span>
          </div>
          <p className="meta-line">
            Conversas salvas neste navegador — reabra e continue com o mesmo
            especialista.
          </p>
          {history.length === 0 ? (
            <p className="meta-line">Nenhum projeto ainda.</p>
          ) : (
            <>
              <ul className="history-list">
                {history.map((session) => (
                  <li key={session.id}>
                    <button
                      type="button"
                      className={`history-item${
                        activeSessionId === session.id ? " history-active" : ""
                      }`}
                      onClick={() => handleReopenSession(session)}
                    >
                      <span className="history-title">
                        {session.fragmentName}
                      </span>
                      <span className="history-preview">
                        {session.title}
                      </span>
                      <span className="history-meta">
                        {turnCountLabel(session)} ·{" "}
                        {new Date(session.updatedAt).toLocaleString()}
                      </span>
                    </button>
                    <div className="history-item-actions">
                      <button
                        type="button"
                        className="btn-link"
                        onClick={() => handleExportSession(session, "md")}
                      >
                        .md
                      </button>
                      <button
                        type="button"
                        className="btn-link"
                        onClick={() => handleExportSession(session, "json")}
                      >
                        .json
                      </button>
                      <button
                        type="button"
                        className="btn-link"
                        onClick={(e) => handleDeleteSession(session.id, e)}
                      >
                        excluir
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleClearHistory}
                >
                  Limpar projetos
                </button>
              </div>
            </>
          )}
        </section>
      ) : null}

      <nav className="stepper stepper-simple" aria-label="Progresso">
        {UI_STEPS.map((step, index) => (
          <span key={step.id} className="stepper-item">
            <span
              className={`step-pill${
                uiStep === step.id
                  ? " step-current"
                  : uiStep > step.id
                    ? " step-done"
                    : ""
              }`}
            >
              {step.id}. {step.label}
            </span>
            {index < UI_STEPS.length - 1 ? (
              <span className="step-arrow" aria-hidden>
                →
              </span>
            ) : null}
          </span>
        ))}
      </nav>

      {showCatalog ? (
        <section
          id="catalog-drawer"
          className="catalog-drawer catalog-drawer-global"
          aria-label="Catálogo de especialistas"
        >
          <div className="catalog-drawer-head">
            <h2>Especialistas disponíveis</h2>
            <button
              type="button"
              className="btn-link"
              onClick={() => setShowCatalog(false)}
            >
              Fechar
            </button>
          </div>
          <p className="meta-line">
            {fragmentCount} fragmentos no catálogo. Filtre e escolha um para
            usar (depois Preparar).
          </p>
          <label htmlFor="catalog-filter" className="field-label">
            Filtrar
          </label>
          <input
            id="catalog-filter"
            type="search"
            className="catalog-filter"
            value={catalogFilter}
            onChange={(e) => setCatalogFilter(e.target.value)}
            placeholder="Nome, id, arquivo ou função…"
            autoComplete="off"
          />
          {filteredCategories.length === 0 ? (
            <p className="status">
              {loading
                ? "Carregando catálogo…"
                : "Nenhum especialista corresponde ao filtro."}
            </p>
          ) : (
            filteredCategories.map((section: CategoryGroup) => (
              <section key={section.name} className="category-section">
                <div className="section-head">
                  <h3>{section.name}</h3>
                  <span className="count">{section.fragments.length}</span>
                </div>
                <div className="grid">
                  {section.fragments.map((fragment) => (
                    <FragmentCard
                      key={fragment.id}
                      fragment={fragment}
                      selected={selectedId === fragment.id}
                      onSelect={handleCatalogSelect}
                    />
                  ))}
                </div>
              </section>
            ))
          )}
        </section>
      ) : null}

      {uiStep === 1 ? (
        <section className="step-panel request-panel">
          <form onSubmit={handleSuggest}>
            <label htmlFor="pedido" className="field-label">
              Pedido
            </label>
            <div className="examples" role="group" aria-label="Exemplos">
              {REQUEST_EXAMPLES.map((ex) => (
                <button
                  key={ex.id}
                  type="button"
                  className="example-chip"
                  disabled={suggesting}
                  onClick={() => applyRequestExample(ex.id)}
                >
                  {ex.label}
                </button>
              ))}
            </div>
            <textarea
              id="pedido"
              rows={4}
              value={requestText}
              onChange={(e) => setRequestText(e.target.value)}
              placeholder="Pedido ou anexe um arquivo…"
            />
            {pendingAttachments.length > 0 ? (
              <ul className="attach-chips">
                {pendingAttachments.map((a) => (
                  <li key={a.id}>
                    <span>{a.name}</span>
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() =>
                        setPendingAttachments((prev) =>
                          prev.filter((x) => x.id !== a.id),
                        )
                      }
                    >
                      remover
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.md,.json,.csv,.pdf,.docx,image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp,.doc,.py,.ts,.tsx,.js,.jsx"
              className="sr-only"
              onChange={(e) => handleFilesSelected(e.target.files)}
            />
            <input
              ref={folderInputRef}
              type="file"
              className="sr-only"
              multiple
              {...({ webkitdirectory: "", directory: "" } as Record<
                string,
                string
              >)}
              onChange={(e) => void handleFolderSelected(e.target.files)}
            />
            <div className="composer-toggles">
              <label className="toggle-chip">
                <input
                  type="checkbox"
                  checked={webSearchOn}
                  disabled={webSearchMeta?.enabled === false}
                  onChange={(e) => setWebSearchOn(e.target.checked)}
                />
                Buscar na web
              </label>
              <label className="toggle-chip">
                <input
                  type="checkbox"
                  checked={useWorkspaceOn}
                  disabled={!workspaceMeta?.enabled}
                  onChange={(e) => setUseWorkspaceOn(e.target.checked)}
                />
                Usar workspace
              </label>
              <label className="toggle-chip">
                <input
                  type="checkbox"
                  checked={includeGitOn}
                  disabled={
                    !workspaceMeta?.enabled ||
                    !runRecipes.some((r) => r.group === "git" && r.ready)
                  }
                  onChange={(e) => setIncludeGitOn(e.target.checked)}
                />
                Incluir Git
              </label>
              <label className="toggle-chip">
                <input
                  type="checkbox"
                  checked={agentToolsOn}
                  disabled={!workspaceMeta?.enabled}
                  onChange={(e) => setAgentToolsOn(e.target.checked)}
                />
                Agente
              </label>
              <label className="toggle-chip">
                <input
                  type="checkbox"
                  checked={suggestDiffOn}
                  onChange={(e) => setSuggestDiffOn(e.target.checked)}
                />
                Sugerir diffs
              </label>
            </div>
            {folderHint ? (
              <p className="meta-line" role="status">
                {folderHint}
              </p>
            ) : null}
            <div className="form-actions form-actions-primary">
              <button
                type="submit"
                disabled={
                  suggesting ||
                  (!requestText.trim() && pendingAttachments.length === 0)
                }
              >
                {suggesting ? "Analisando…" : "Continuar"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={suggesting}
                onClick={() => fileInputRef.current?.click()}
              >
                Anexar
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={suggesting}
                onClick={() => folderInputRef.current?.click()}
                title="Seleciona arquivos de código da pasta (não grava no disco)"
              >
                Pasta local
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowCatalog((v) => !v)}
              >
                {showCatalog ? "Ocultar catálogo" : "Listar especialistas"}
              </button>
            </div>
          </form>
          {selected ? (
            <div className="selection-banner" aria-live="polite">
              <p>
                Selecionado: <strong>{selected.name}</strong>
                {selected.filename ? (
                  <>
                    {" "}
                    · <code>{selected.filename}</code>
                  </>
                ) : null}
              </p>
              {selectedPrereqs.length > 0 ? (
                <div className="prereq-warning" role="status">
                  {selectedPrereqs.map((p) => (
                    <p key={p.code}>{p.message}</p>
                  ))}
                </div>
              ) : null}
              <div className="form-actions form-actions-primary">
                <button
                  type="button"
                  disabled={
                    pipelineBusy ||
                    !selectedId ||
                    (!requestText.trim() && pendingAttachments.length === 0)
                  }
                  onClick={() => void handleForge()}
                  title={
                    !requestText.trim() && pendingAttachments.length === 0
                      ? "Escreva um pedido acima antes de preparar"
                      : "Preparar conversa com este especialista"
                  }
                >
                  {pipelineBusy ? "Preparando…" : "Preparar com este"}
                </button>
              </div>
            </div>
          ) : null}
          {pipelineError && uiStep === 1 ? (
            <p className="status error" role="alert">
              {pipelineError}
            </p>
          ) : null}
          {suggestError ? (
            <p className="status error" role="alert">
              {suggestError}
            </p>
          ) : null}
          {loading ? <p className="meta-line">Carregando catálogo…</p> : null}
          {error ? (
            <p className="status error" role="alert">
              {error}
            </p>
          ) : null}
        </section>
      ) : null}

      {uiStep === 2 ? (
        <section className="step-panel suggestions-panel">
          <div className="section-head">
            <h2>Escolha o especialista</h2>
            <button
              type="button"
              className="btn-link"
              onClick={handleNewRequest}
            >
              Voltar ao pedido
            </button>
          </div>

          {suggestMeta?.projectSniff &&
          (suggestMeta.projectSniff.summary ||
            suggestMeta.projectSniff.stacks?.length) ? (
            <div className="sniff-banner status info" role="status">
              <p>
                Detectei:{" "}
                <strong>
                  {suggestMeta.projectSniff.summary ||
                    suggestMeta.projectSniff.stacks.join(" + ")}
                </strong>
                {selected ? (
                  <>
                    {" "}
                    · especialista sugerido: <strong>{selected.name}</strong>
                  </>
                ) : null}
                {typeof suggestMeta.projectSniff.confidence === "number" ? (
                  <span className="sniff-conf">
                    {" "}
                    (confiança{" "}
                    {Math.round(suggestMeta.projectSniff.confidence * 100)}%)
                  </span>
                ) : null}
              </p>
              {suggestMeta.autoActivateRecommended ? (
                <button
                  type="button"
                  className="btn-primary-inline"
                  disabled={pipelineBusy || !selectedId}
                  onClick={() => void handleActivateAndHelp()}
                >
                  {pipelineBusy ? "Ativando…" : "Ativar e ajudar"}
                </button>
              ) : null}
            </div>
          ) : null}

          {suggestMeta?.aiInterpreted && suggestMeta.interpretation?.goal ? (
            <div className="interpretation-box" aria-live="polite">
              <h3>O que entendi</h3>
              <p>{suggestMeta.interpretation.goal}</p>
            </div>
          ) : null}
          {suggestMeta?.interpretation?.clarifying_question ? (
            <p className="status warning" role="status">
              {suggestMeta.interpretation.clarifying_question} Você pode voltar
              e ajustar o pedido.
            </p>
          ) : null}
          {suggestMeta?.warning ? (
            <p className="status warning" role="status">
              {suggestMeta.warning}
            </p>
          ) : null}

          {suggestions && suggestions.length > 0 ? (
            <ul className="suggestion-list">
              {suggestions.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className={`suggestion-item${
                      selectedId === s.id ? " suggestion-selected" : ""
                    }`}
                    onClick={() => handleCatalogSelect(s.id)}
                  >
                    <div className="suggestion-top">
                      <strong>{s.name}</strong>
                      <span className="score">{s.category}</span>
                    </div>
                    <p>{s.explanation}</p>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="status">
              Nenhuma sugestão automática. Abra o catálogo e escolha um
              especialista.
            </p>
          )}

          {selected ? (
            <div className="selection-banner" aria-live="polite">
              <p>
                Selecionado: <strong>{selected.name}</strong>
              </p>
              {selectedPrereqs.length > 0 ? (
                <div className="prereq-warning" role="status">
                  {selectedPrereqs.map((p) => (
                    <p key={p.code}>{p.message}</p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          <div className="form-actions form-actions-primary">
            <button
              type="button"
              disabled={
                pipelineBusy ||
                !selectedId ||
                (!requestText.trim() && pendingAttachments.length === 0)
              }
              onClick={handleForge}
            >
              {pipelineBusy ? "Preparando…" : "Preparar"}
            </button>
            {suggestMeta?.autoActivateRecommended ? (
              <button
                type="button"
                className="btn-secondary"
                disabled={pipelineBusy || !selectedId}
                onClick={() => void handleActivateAndHelp()}
              >
                Ativar e ajudar
              </button>
            ) : null}
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowCatalog((v) => !v)}
            >
              {showCatalog
                ? "Ocultar catálogo"
                : "Ver todos os especialistas"}
            </button>
          </div>
          {pipelineError ? (
            <p className="status error" role="alert">
              {pipelineError}
              {pipelineRetryable ? (
                <>
                  {" "}
                  <button
                    type="button"
                    className="btn-link"
                    disabled={pipelineBusy}
                    onClick={() => {
                      setPipelineError(null);
                      setPipelineRetryable(false);
                      void handleForge();
                    }}
                  >
                    Tentar de novo
                  </button>
                </>
              ) : null}
            </p>
          ) : null}

          <button
            type="button"
            className="btn-link details-toggle"
            onClick={() => setShowDetails((v) => !v)}
          >
            {showDetails ? "Ocultar detalhes técnicos" : "Detalhes técnicos"}
          </button>
          {showDetails ? (
            <div className="meta-bar" aria-live="polite">
              <div className="chip-row">
                <span className="chip-label">Stacks</span>
                {suggestMeta?.stacks.length ? (
                  suggestMeta.stacks.map((s) => (
                    <span key={s} className="chip">
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="chip muted">—</span>
                )}
              </div>
              <div className="chip-row">
                <span className="chip-label">Arquivo</span>
                <span className="chip">
                  {selected ? <code>{selected.filename}</code> : "—"}
                </span>
                <span className="chip-label">Modo</span>
                <span className="chip">
                  {suggestMeta?.mode === "hybrid" ? "híbrido" : "regras"}
                </span>
              </div>
              <p className="cost-note">
                Sugestão ambígua pode usar +1 chamada; preparar+gerar = até 2.
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      {uiStep === 3 ? (
        <>
          {activatedDoc && phase === "result" ? (
            <section className="activation-banner" aria-live="polite">
              <h2>Documento ativado</h2>
              <p>
                <strong>{activatedDoc.name}</strong>
                {activatedDoc.hash ? (
                  <>
                    {" "}
                    · <code>{activatedDoc.hash}</code>
                  </>
                ) : null}
              </p>
            </section>
          ) : null}

          {phase === "review" || (phase === "result" && !runResult) ? (
            <section className="step-panel pipeline-panel">
              <div className="section-head">
                <h2>Revise e comece a conversar</h2>
                <span className="count">
                  {forgeInfo?.fragment_name ?? selected?.name}
                </span>
              </div>
              {forgeInfo && !forgeInfo.ai_executed ? (
                <p className="status warning" role="status">
                  {forgeInfo.warning ??
                    "Texto preparado localmente; a IA ainda não rodou."}
                </p>
              ) : null}
              {activationInfo?.detected ? (
                <div className="activation-box" aria-live="polite">
                  <h3>Documento reconhecido</h3>
                  <p>
                    <strong>{activationInfo.name}</strong>
                  </p>
                  {activationInfo.activation_hash ? (
                    <p className="meta-line">
                      Hash: <code>{activationInfo.activation_hash}</code>
                    </p>
                  ) : null}
                  {activationInfo.notes ? (
                    <p className="meta-line">{activationInfo.notes}</p>
                  ) : null}
                </div>
              ) : null}
              <label htmlFor="draft" className="field-label">
                Texto preparado (opcional editar)
              </label>
              <textarea
                id="draft"
                ref={draftRef}
                rows={8}
                value={draft}
                readOnly={!draftEditable || phase === "result"}
                onChange={(e) => setDraft(e.target.value)}
              />
              <div className="form-actions form-actions-primary">
                <button
                  type="button"
                  disabled={pipelineBusy || phase === "result" || !draft.trim()}
                  onClick={() => {
                    void (async () => {
                      setPipelineBusy(true);
                      try {
                        if (
                          forgeInfo?.mode === "activation" ||
                          activationInfo
                        ) {
                          await openConversationAfterPrep(
                            forgeInfo ?? {
                              draft,
                              request: requestText.trim(),
                              fragment_id: selectedId!,
                              fragment_name: selected?.name ?? "",
                              mode: "activation",
                              ai_executed: false,
                              activation: activationInfo,
                            },
                          );
                        } else {
                          await handleRun();
                        }
                      } finally {
                        setPipelineBusy(false);
                      }
                    })();
                  }}
                >
                  {pipelineBusy && phase === "review"
                    ? "Abrindo conversa…"
                    : forgeInfo?.mode === "activation" || activationInfo
                      ? "Começar conversa"
                      : "Gerar resposta"}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={phase === "result" || draftEditable}
                  onClick={handleEditDraft}
                >
                  Editar
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={pipelineBusy}
                  onClick={handleBackToSpecialist}
                >
                  Voltar
                </button>
              </div>
              {copyNotice ? <p className="meta-line">{copyNotice}</p> : null}
              {pipelineError ? (
                <p className="status error" role="alert">
                  {pipelineError}
                  {pipelineRetryable ? (
                    <>
                      {" "}
                      <button
                        type="button"
                        className="btn-link"
                        disabled={pipelineBusy}
                        onClick={() => {
                          setPipelineError(null);
                          setPipelineRetryable(false);
                          void handleRun();
                        }}
                      >
                        Tentar de novo
                      </button>
                    </>
                  ) : null}
                </p>
              ) : null}
            </section>
          ) : null}

          {phase === "result" && runResult ? (
            <section className="step-panel pipeline-panel result-panel">
              <div className="section-head">
                <h2>Conversando com {runResult.fragment_name}</h2>
                <span className="count">
                  {activatedDoc ? "ativado" : "especialista"}
                </span>
              </div>
              {!runResult.ai_executed ? (
                <p className="status warning" role="status">
                  {runResult.warning ??
                    "Modo prévia: a IA não foi executada."}
                </p>
              ) : null}
              {ragInfo.used || runResult.rag_used ? (
                <p className="status info" role="status">
                  Contexto recuperado:{" "}
                  {ragInfo.chunks || runResult.rag_chunks || 0} trechos do
                  especialista (RAG).
                </p>
              ) : null}
              {fragmentTruncated || runResult.fragment_truncated ? (
                <p className="status warning" role="status">
                  Documento grande: o contexto do `.md` foi compactado/recuperado
                  para caber no limite do provedor (Groq). A conversa continua
                  normalmente — digite abaixo o que quiser.
                </p>
              ) : null}

              <div className="chat-panel">
              <div className="chat-thread" aria-live="polite">
                {(chatMessages.length
                  ? chatMessages
                  : [
                      {
                        role: "user" as const,
                        content: requestText.trim(),
                      },
                      {
                        role: "assistant" as const,
                        content: runResult.response,
                      },
                    ]
                ).map((turn, idx) => (
                  <div
                    key={`${turn.role}-${idx}`}
                    className={`chat-bubble chat-${turn.role}`}
                  >
                    <span className="chat-role">
                      {turn.role === "user" ? "Você" : "Especialista"}
                    </span>
                    {turn.role === "assistant" ? (
                      <div className="chat-md">
                        {turn.content ? (
                          <ReactMarkdown components={mdComponents}>
                            {turn.content}
                          </ReactMarkdown>
                        ) : chatTyping ? (
                          <span className="typing-dots" aria-label="Digitando">
                            <span />
                            <span />
                            <span />
                          </span>
                        ) : null}
                      </div>
                    ) : (
                      <pre className="chat-content">{turn.content}</pre>
                    )}
                  </div>
                ))}
                {chatTyping &&
                chatMessages[chatMessages.length - 1]?.role === "assistant" &&
                chatMessages[chatMessages.length - 1]?.content === "" ? null : chatTyping &&
                  chatMessages[chatMessages.length - 1]?.role !== "assistant" ? (
                  <div className="chat-bubble chat-assistant">
                    <span className="chat-role">Especialista</span>
                    <span className="typing-dots" aria-label="Digitando">
                      <span />
                      <span />
                      <span />
                    </span>
                  </div>
                ) : null}
                {toolSteps.length > 0 ? (
                  <aside className="tool-trace" aria-label="Ferramentas do agente">
                    <strong>Agente</strong>
                    <ol>
                      {toolSteps.map((step, i) => (
                        <li key={`${step.name}-${i}`}>
                          <span className={step.ok === false ? "tool-fail" : "tool-ok"}>
                            {step.round != null ? `#${step.round} ` : ""}
                            {step.name}
                            {step.ok === false ? " (falhou)" : ""}
                          </span>
                          {step.preview ? (
                            <pre className="tool-preview">{step.preview}</pre>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  </aside>
                ) : null}
                {lastSandboxOut ? (
                  <div className="sandbox-followup">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={sendSandboxToSpecialist}
                    >
                      Enviar resultado ao especialista
                    </button>
                  </div>
                ) : null}
                {workspaceMeta?.enabled && runRecipes.length > 0 ? (
                  <>
                    <div className="verify-bar" role="group" aria-label="Git">
                      <span className="chip-label">Git</span>
                      {runRecipes
                        .filter(
                          (r) =>
                            r.ready &&
                            (r.group === "git" ||
                              r.id === "git_status" ||
                              r.id === "git_diff" ||
                              r.id === "git_log_oneline"),
                        )
                        .filter((r) => r.id !== "git_diff_stat")
                        .map((r) => (
                          <button
                            key={r.id}
                            type="button"
                            className="btn-secondary"
                            disabled={verifyBusy || chatBusy || commitSuggestBusy}
                            title={r.label}
                            onClick={() => void handleWorkspaceVerify(r.id)}
                          >
                            {verifyBusy ? "…" : r.label}
                          </button>
                        ))}
                      {runRecipes.some(
                        (r) => r.id === "git_status" && r.ready,
                      ) ? (
                        <button
                          type="button"
                          className="btn-secondary"
                          disabled={verifyBusy || chatBusy || commitSuggestBusy}
                          title="Gera texto de mensagem de commit (não executa git commit)"
                          onClick={() => void handleSuggestCommit()}
                        >
                          {commitSuggestBusy ? "…" : "Sugerir commit"}
                        </button>
                      ) : null}
                    </div>
                    <div
                      className="verify-bar"
                      role="group"
                      aria-label="Verificação"
                    >
                      <span className="chip-label">Verificar</span>
                      {runRecipes
                        .filter((r) => r.ready && r.group !== "git")
                        .map((r) => (
                          <button
                            key={r.id}
                            type="button"
                            className="btn-secondary"
                            disabled={verifyBusy || chatBusy}
                            title={r.label}
                            onClick={() => void handleWorkspaceVerify(r.id)}
                          >
                            {verifyBusy ? "…" : r.label}
                          </button>
                        ))}
                      {lastVerifyOut ? (
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={sendVerifyToSpecialist}
                        >
                          Enviar log ao especialista
                        </button>
                      ) : null}
                    </div>
                  </>
                ) : null}
                {suggestedDiffBlocks.length > 0 && !chatTyping ? (
                  <DiffPanel
                    key={suggestedDiffBlocks.map((b) => b.id).join("|")}
                    blocks={suggestedDiffBlocks}
                    workspaceEnabled={Boolean(workspaceMeta?.enabled)}
                    workspaceName={workspaceMeta?.root_name}
                    onNotice={(msg) => {
                      setCopyNotice(msg);
                      window.setTimeout(() => setCopyNotice(null), 4000);
                    }}
                    onApplied={() => {
                      setPostApplyVerify(true);
                      setCopyNotice(
                        "Diffs aplicados. Use «Verificar agora» abaixo.",
                      );
                      window.setTimeout(() => setCopyNotice(null), 4000);
                    }}
                  />
                ) : null}
                {postApplyVerify && workspaceMeta?.enabled ? (
                  <div className="post-apply-bar" role="status">
                    <span>Diffs gravados.</span>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={verifyBusy || chatBusy || !preferredVerifyRecipe()}
                      onClick={() => {
                        const id = preferredVerifyRecipe();
                        if (id) void handleWorkspaceVerify(id);
                      }}
                    >
                      Verificar agora
                    </button>
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() => setPostApplyVerify(false)}
                    >
                      dispensar
                    </button>
                  </div>
                ) : null}
                <div ref={chatEndRef} />
              </div>

              <form className="chat-composer chat-composer-sticky" onSubmit={handleChatSend}>
                {workspaceMeta?.enabled ? (
                  <WorkspacePanel
                    enabled
                    onAddContext={(path) => pickContextPath(path)}
                  />
                ) : null}
                <label htmlFor="chat-input" className="field-label">
                  Continue perguntando
                  {workspaceMeta?.enabled ? (
                    <span className="field-hint">
                      {" "}
                      · @arquivo ou @pasta/ (contexto do workspace)
                    </span>
                  ) : null}
                </label>
                <div className="composer-input-wrap">
                  <textarea
                    id="chat-input"
                    rows={3}
                    value={chatInput}
                    disabled={chatBusy}
                    onChange={(e) => {
                      const v = e.target.value;
                      setChatInput(v);
                      scheduleAtSearch(v);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Escape" && atOpen) {
                        e.preventDefault();
                        setAtOpen(false);
                        return;
                      }
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (!chatBusy) {
                          e.currentTarget.form?.requestSubmit();
                        }
                      }
                    }}
                    placeholder="Sua pergunta… @backend/ ou @arquivo.py · Enter envia"
                  />
                  {atOpen && workspaceMeta?.enabled ? (
                    <ul className="at-file-menu" role="listbox" aria-label="Arquivos e pastas do workspace">
                      {atHits.length === 0 ? (
                        <li className="at-file-empty">Buscando…</li>
                      ) : (
                        atHits.map((hit) => {
                          const isDir =
                            hit.kind === "dir" || hit.path.endsWith("/");
                          return (
                            <li key={hit.path}>
                              <button
                                type="button"
                                onClick={() =>
                                  pickContextPath(
                                    isDir
                                      ? hit.path.replace(/\/?$/, "/")
                                      : hit.path,
                                  )
                                }
                              >
                                <span className="workspace-kind">
                                  {isDir ? "dir" : "file"}
                                </span>{" "}
                                {hit.path}
                              </button>
                            </li>
                          );
                        })
                      )}
                    </ul>
                  ) : null}
                </div>
                {contextPaths.length > 0 ? (
                  <ul className="attach-chips context-chips" aria-label="Contexto @arquivo/@pasta">
                    {contextPaths.map((path) => (
                      <li key={path}>
                        <span>
                          @{path}
                          {path.endsWith("/") ? " (pasta)" : ""}
                        </span>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={() =>
                            setContextPaths((prev) =>
                              prev.filter((p) => p !== path),
                            )
                          }
                        >
                          remover
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {pendingAttachments.length > 0 ? (
                  <ul className="attach-chips">
                    {pendingAttachments.map((a) => (
                      <li key={a.id}>
                        <span>{a.name}</span>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={() =>
                            setPendingAttachments((prev) =>
                              prev.filter((x) => x.id !== a.id),
                            )
                          }
                        >
                          remover
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".txt,.md,.json,.csv,.pdf,.docx,image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp,.doc,.py,.ts,.tsx,.js,.jsx"
                  className="sr-only"
                  onChange={(e) => handleFilesSelected(e.target.files)}
                />
                <input
                  ref={folderInputRef}
                  type="file"
                  className="sr-only"
                  multiple
                  {...({ webkitdirectory: "", directory: "" } as Record<
                    string,
                    string
                  >)}
                  onChange={(e) => void handleFolderSelected(e.target.files)}
                />
                <div className="composer-toggles">
                  <label className="toggle-chip">
                    <input
                      type="checkbox"
                      checked={webSearchOn}
                      disabled={chatBusy || webSearchMeta?.enabled === false}
                      onChange={(e) => setWebSearchOn(e.target.checked)}
                    />
                    Buscar na web
                  </label>
                  <label className="toggle-chip">
                    <input
                      type="checkbox"
                      checked={useWorkspaceOn}
                      disabled={chatBusy || !workspaceMeta?.enabled}
                      onChange={(e) => setUseWorkspaceOn(e.target.checked)}
                    />
                    Usar workspace
                  </label>
                  <label className="toggle-chip">
                    <input
                      type="checkbox"
                      checked={includeGitOn}
                      disabled={
                        chatBusy ||
                        !workspaceMeta?.enabled ||
                        !runRecipes.some((r) => r.group === "git" && r.ready)
                      }
                      onChange={(e) => setIncludeGitOn(e.target.checked)}
                    />
                    Incluir Git
                  </label>
                  <label className="toggle-chip">
                    <input
                      type="checkbox"
                      checked={agentToolsOn}
                      disabled={chatBusy || !workspaceMeta?.enabled}
                      onChange={(e) => setAgentToolsOn(e.target.checked)}
                    />
                    Agente
                  </label>
                  <label className="toggle-chip">
                    <input
                      type="checkbox"
                      checked={suggestDiffOn}
                      disabled={chatBusy}
                      onChange={(e) => setSuggestDiffOn(e.target.checked)}
                    />
                    Sugerir diffs
                  </label>
                </div>
                {folderHint ? (
                  <p className="meta-line" role="status">
                    {folderHint}
                  </p>
                ) : null}
                <div className="form-actions form-actions-primary">
                  <button type="submit" disabled={chatBusy}>
                    {chatBusy ? "Enviando…" : "Enviar"}
                  </button>
                  {chatBusy ? (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={stopChatGeneration}
                    >
                      Parar
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={chatBusy}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Anexar
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={chatBusy}
                    onClick={() => folderInputRef.current?.click()}
                    title="Seleciona arquivos de código da pasta"
                  >
                    Pasta local
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleCopy("response")}
                  >
                    Copiar última
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleExport("md")}
                  >
                    Exportar .md
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleExport("json")}
                  >
                    Exportar .json
                  </button>
                  <button type="button" onClick={handleNewRequest}>
                    Novo pedido
                  </button>
                </div>
              </form>
              </div>
              {chatWarning ? (
                <p className="status warning" role="status">
                  {chatWarning}
                </p>
              ) : null}
              {lastUsage ? (
                <p className="meta-line usage-line" title="Estimativa local (~4 chars/token)">
                  Último turno ≈{" "}
                  {(lastUsage.prompt_tokens_approx ?? 0) +
                    (lastUsage.completion_tokens_approx ?? 0)}{" "}
                  tokens
                  {typeof lastUsage.prompt_chars === "number"
                    ? ` · ${lastUsage.prompt_chars + (lastUsage.completion_chars ?? 0)} chars`
                    : ""}
                </p>
              ) : null}
              {chatError ? (
                <p className="status error" role="alert">
                  {chatError}
                  {chatRetryable ? (
                    <>
                      {" "}
                      <button
                        type="button"
                        className="btn-link"
                        disabled={chatBusy}
                        onClick={() => {
                          setChatError(null);
                          setChatRetryable(false);
                          // Re-submit last user turn if composer empty: nudge user
                          void (document.getElementById("chat-input") as HTMLTextAreaElement | null)
                            ?.form?.requestSubmit();
                        }}
                      >
                        Tentar de novo
                      </button>
                    </>
                  ) : null}
                </p>
              ) : null}
              {copyNotice ? <p className="meta-line">{copyNotice}</p> : null}
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
