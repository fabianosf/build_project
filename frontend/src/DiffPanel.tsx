import { useState } from "react";
import { applyWorkspaceDiffs } from "./api";
import {
  blocksToPatches,
  joinDiffBodies,
  type DiffBlock,
} from "./diffBlocks";

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

type Props = {
  blocks: DiffBlock[];
  workspaceEnabled?: boolean;
  workspaceName?: string | null;
  onNotice?: (message: string) => void;
};

export function DiffPanel({
  blocks,
  workspaceEnabled = false,
  workspaceName,
  onNotice,
}: Props) {
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(blocks.map((b) => [b.id, true])),
  );
  const [applying, setApplying] = useState(false);

  if (!blocks.length) return null;

  async function copyOne(block: DiffBlock) {
    const ok = await copyText(block.body);
    onNotice?.(
      ok
        ? `Diff copiado${block.files[0] ? `: ${block.files[0]}` : ""}.`
        : "Falha ao copiar.",
    );
  }

  async function copyAll() {
    const ok = await copyText(joinDiffBodies(blocks));
    onNotice?.(
      ok ? `${blocks.length} diff(s) copiado(s).` : "Falha ao copiar.",
    );
  }

  async function applyAll() {
    if (!workspaceEnabled) {
      onNotice?.("Defina WORKSPACE_ROOT no .env e reinicie o backend.");
      return;
    }
    const label = workspaceName || "WORKSPACE_ROOT";
    const okConfirm = window.confirm(
      `Isso altera arquivos em «${label}». Backups .bak serão criados. Continuar?`,
    );
    if (!okConfirm) return;
    setApplying(true);
    try {
      const result = await applyWorkspaceDiffs(blocksToPatches(blocks));
      const fails = result.results.filter((r) => !r.ok);
      if (fails.length === 0) {
        onNotice?.(
          `Aplicados ${result.applied} arquivo(s) no workspace.`,
        );
      } else {
        onNotice?.(
          `Aplicados ${result.applied}; falhas: ${fails
            .map((f) => `${f.path || "?"}: ${f.error || "erro"}`)
            .join(" · ")}`,
        );
      }
    } catch (err) {
      onNotice?.(err instanceof Error ? err.message : "Falha ao aplicar diffs.");
    } finally {
      setApplying(false);
    }
  }

  function toggle(id: string) {
    setOpen((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  return (
    <aside className="diff-panel" aria-label="Diffs sugeridos">
      <div className="diff-panel-head">
        <div>
          <strong>Diffs sugeridos</strong>
          <p className="diff-panel-note">
            Sugestão até você confirmar. Copie ou aplique no workspace.
          </p>
        </div>
        <div className="diff-panel-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void copyAll()}
          >
            Copiar todos
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={!workspaceEnabled || applying}
            title={
              workspaceEnabled
                ? "Grava patches em WORKSPACE_ROOT (com .bak)"
                : "Configure WORKSPACE_ROOT no .env"
            }
            onClick={() => void applyAll()}
          >
            {applying ? "Aplicando…" : "Aplicar no workspace"}
          </button>
        </div>
      </div>
      <ul className="diff-panel-list">
        {blocks.map((block, index) => {
          const label =
            block.files.length > 0
              ? block.files.join(", ")
              : `Bloco ${index + 1}`;
          const isOpen = open[block.id] !== false;
          return (
            <li key={block.id} className="diff-panel-item">
              <div className="diff-panel-item-bar">
                <button
                  type="button"
                  className="btn-link diff-toggle"
                  aria-expanded={isOpen}
                  onClick={() => toggle(block.id)}
                >
                  {isOpen ? "▾" : "▸"} {label}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void copyOne(block)}
                >
                  Copiar
                </button>
              </div>
              {isOpen ? (
                <pre className="diff-panel-pre">
                  <code>{block.body}</code>
                </pre>
              ) : null}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
