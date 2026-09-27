/** Browser-local conversation projects (localStorage). No backend. */

export type SuggestMode = "deterministic" | "hybrid";

export type SessionTurn = {
  role: "user" | "assistant";
  content: string;
};

export type RunSession = {
  id: string;
  createdAt: string;
  /** Last activity — used for sorting projects. */
  updatedAt: string;
  /** Short label for the projects list. */
  title: string;
  request: string;
  selectedId: string;
  fragmentName: string;
  fragmentFilename: string;
  suggestMode: SuggestMode | null;
  intents: string[];
  stacks: string[];
  interpretationGoal: string | null;
  draft: string;
  /** Last assistant reply (compat + quick preview). */
  response: string;
  runMode: "preview" | "llm";
  aiExecuted: boolean;
  /** Full chat thread for reopen. */
  messages: SessionTurn[];
  /** Attachment filenames seen in the session (no file bytes). */
  attachmentNames: string[];
  documentRecognized: boolean;
  /** Lightweight product telemetry (local only). */
  telemetry: SessionTelemetry | null;
};

export type SessionTelemetry = {
  suggestedId: string | null;
  chosenId: string | null;
  msSuggest: number | null;
  msRun: number | null;
  tokensApprox: number | null;
  /** True when the user picked a different specialist than auto-suggest. */
  corrected: boolean;
};

const STORAGE_KEY = "orquestrador.history.v2";
const LEGACY_KEY = "orquestrador.history.v1";
const MAX_SESSIONS = 40;

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `s-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function deriveTitle(request: string, fragmentName: string): string {
  const base = (request || "").trim().replace(/\s+/g, " ");
  if (base) {
    return base.length > 48 ? `${base.slice(0, 48)}…` : base;
  }
  return fragmentName || "Projeto";
}

function normalizeSession(raw: unknown): RunSession | null {
  if (!raw || typeof raw !== "object") return null;
  const item = raw as Record<string, unknown>;
  if (typeof item.id !== "string" || typeof item.request !== "string") {
    return null;
  }
  const createdAt =
    typeof item.createdAt === "string"
      ? item.createdAt
      : new Date().toISOString();
  const updatedAt =
    typeof item.updatedAt === "string" ? item.updatedAt : createdAt;
  const fragmentName =
    typeof item.fragmentName === "string" ? item.fragmentName : "Especialista";
  const response = typeof item.response === "string" ? item.response : "";
  let messages: SessionTurn[] = [];
  if (Array.isArray(item.messages)) {
    messages = item.messages.filter(
      (m): m is SessionTurn =>
        Boolean(m) &&
        typeof m === "object" &&
        ((m as SessionTurn).role === "user" ||
          (m as SessionTurn).role === "assistant") &&
        typeof (m as SessionTurn).content === "string",
    );
  }
  if (messages.length === 0) {
    const req = item.request as string;
    if (req) messages.push({ role: "user", content: req });
    if (response) messages.push({ role: "assistant", content: response });
  }
  const attachmentNames = Array.isArray(item.attachmentNames)
    ? item.attachmentNames.filter((n): n is string => typeof n === "string")
    : [];
  let telemetry: SessionTelemetry | null = null;
  if (item.telemetry && typeof item.telemetry === "object") {
    const t = item.telemetry as Record<string, unknown>;
    telemetry = {
      suggestedId: typeof t.suggestedId === "string" ? t.suggestedId : null,
      chosenId: typeof t.chosenId === "string" ? t.chosenId : null,
      msSuggest: typeof t.msSuggest === "number" ? t.msSuggest : null,
      msRun: typeof t.msRun === "number" ? t.msRun : null,
      tokensApprox: typeof t.tokensApprox === "number" ? t.tokensApprox : null,
      corrected: Boolean(t.corrected),
    };
  }
  return {
    id: item.id,
    createdAt,
    updatedAt,
    title:
      typeof item.title === "string" && item.title.trim()
        ? item.title
        : deriveTitle(item.request as string, fragmentName),
    request: item.request,
    selectedId:
      typeof item.selectedId === "string" ? item.selectedId : "",
    fragmentName,
    fragmentFilename:
      typeof item.fragmentFilename === "string" ? item.fragmentFilename : "",
    suggestMode:
      item.suggestMode === "deterministic" || item.suggestMode === "hybrid"
        ? item.suggestMode
        : null,
    intents: Array.isArray(item.intents)
      ? item.intents.filter((x): x is string => typeof x === "string")
      : [],
    stacks: Array.isArray(item.stacks)
      ? item.stacks.filter((x): x is string => typeof x === "string")
      : [],
    interpretationGoal:
      typeof item.interpretationGoal === "string"
        ? item.interpretationGoal
        : null,
    draft: typeof item.draft === "string" ? item.draft : "",
    response,
    runMode: item.runMode === "preview" ? "preview" : "llm",
    aiExecuted: Boolean(item.aiExecuted),
    messages,
    attachmentNames,
    documentRecognized: Boolean(item.documentRecognized),
    telemetry,
  };
}

function readAll(): RunSession[] {
  try {
    let raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const legacy = localStorage.getItem(LEGACY_KEY);
      if (legacy) {
        raw = legacy;
        const migrated = (JSON.parse(legacy) as unknown[]);
        const sessions = migrated
          .map(normalizeSession)
          .filter((s): s is RunSession => Boolean(s));
        writeAll(sessions);
        localStorage.removeItem(LEGACY_KEY);
        return sessions;
      }
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(normalizeSession)
      .filter((s): s is RunSession => Boolean(s));
  } catch {
    return [];
  }
}

function writeAll(sessions: RunSession[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function listSessions(): RunSession[] {
  return readAll().sort(
    (a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt),
  );
}

export type SaveSessionInput = Omit<
  RunSession,
  "id" | "createdAt" | "updatedAt" | "title" | "messages" | "attachmentNames" | "documentRecognized" | "telemetry"
> & {
  id?: string;
  createdAt?: string;
  updatedAt?: string;
  title?: string;
  messages?: SessionTurn[];
  attachmentNames?: string[];
  documentRecognized?: boolean;
  telemetry?: SessionTelemetry | null;
};

export function saveSession(input: SaveSessionInput): RunSession {
  const now = new Date().toISOString();
  const existing = input.id
    ? readAll().find((s) => s.id === input.id)
    : undefined;
  const messages =
    input.messages ??
    existing?.messages ??
    ([
      input.request
        ? { role: "user" as const, content: input.request }
        : null,
      input.response
        ? { role: "assistant" as const, content: input.response }
        : null,
    ].filter(Boolean) as SessionTurn[]);
  const lastAssistant = [...messages]
    .reverse()
    .find((m) => m.role === "assistant");
  const session: RunSession = {
    id: input.id ?? existing?.id ?? newId(),
    createdAt: input.createdAt ?? existing?.createdAt ?? now,
    updatedAt: input.updatedAt ?? now,
    title:
      input.title ??
      existing?.title ??
      deriveTitle(input.request, input.fragmentName),
    request: input.request,
    selectedId: input.selectedId,
    fragmentName: input.fragmentName,
    fragmentFilename: input.fragmentFilename,
    suggestMode: input.suggestMode,
    intents: input.intents,
    stacks: input.stacks,
    interpretationGoal: input.interpretationGoal,
    draft: input.draft,
    response: lastAssistant?.content ?? input.response,
    runMode: input.runMode,
    aiExecuted: input.aiExecuted,
    messages,
    attachmentNames:
      input.attachmentNames ?? existing?.attachmentNames ?? [],
    documentRecognized:
      input.documentRecognized ?? existing?.documentRecognized ?? false,
    telemetry: input.telemetry ?? existing?.telemetry ?? null,
  };
  const next = [
    session,
    ...readAll().filter((s) => s.id !== session.id),
  ].slice(0, MAX_SESSIONS);
  writeAll(next);
  return session;
}

/** Update only the chat thread of an existing project (or create if missing). */
export function upsertSessionThread(
  id: string | null,
  patch: SaveSessionInput & { messages: SessionTurn[] },
): RunSession {
  return saveSession({
    ...patch,
    id: id ?? undefined,
  });
}

export function clearSessions(): void {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(LEGACY_KEY);
}

export function deleteSession(id: string): void {
  writeAll(readAll().filter((s) => s.id !== id));
}

export function sessionToMarkdown(session: RunSession): string {
  const lines = [
    `# Projeto — ${session.fragmentName}`,
    "",
    `- Título: ${session.title}`,
    `- Criado: ${session.createdAt}`,
    `- Atualizado: ${session.updatedAt}`,
    `- Fragmento: ${session.fragmentName} (\`${session.fragmentFilename}\`)`,
    `- Modo sugestão: ${session.suggestMode ?? "—"}`,
    `- Modo execução: ${session.runMode}${session.aiExecuted ? " (IA)" : " (prévia)"}`,
    `- Turns: ${session.messages.length}`,
    "",
    "## Pedido inicial",
    "",
    session.request || "—(só anexos)—",
    "",
  ];
  if (session.attachmentNames.length) {
    lines.push(
      "## Anexos (nomes)",
      "",
      ...session.attachmentNames.map((n) => `- ${n}`),
      "",
    );
  }
  if (session.interpretationGoal) {
    lines.push("## Interpretação", "", session.interpretationGoal, "");
  }
  if (session.intents.length || session.stacks.length) {
    lines.push(
      "## Metadados",
      "",
      `- Intenções: ${session.intents.join(", ") || "—"}`,
      `- Stacks: ${session.stacks.join(", ") || "—"}`,
      "",
    );
  }
  if (session.draft.trim()) {
    lines.push(
      "## Draft",
      "",
      "```",
      session.draft,
      "```",
      "",
    );
  }
  lines.push("## Conversa", "");
  for (const turn of session.messages) {
    const who = turn.role === "user" ? "Você" : "Especialista";
    lines.push(`### ${who}`, "", turn.content, "");
  }
  return lines.join("\n");
}

export function sessionToJson(session: RunSession): string {
  return `${JSON.stringify(session, null, 2)}\n`;
}

export function downloadText(
  filename: string,
  content: string,
  mime: string,
): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function exportFilename(session: RunSession, ext: "md" | "json"): string {
  const stamp = (session.updatedAt || session.createdAt)
    .slice(0, 19)
    .replace(/[:T]/g, "-");
  const slug = session.fragmentName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
  return `projeto-${stamp}-${slug || "fragmento"}.${ext}`;
}

export function turnCountLabel(session: RunSession): string {
  const n = session.messages.length;
  return n === 1 ? "1 mensagem" : `${n} mensagens`;
}
