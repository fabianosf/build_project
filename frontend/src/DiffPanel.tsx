import { useMemo, useState } from "react";
import { applyWorkspaceDiffs, type ApplyDiffResult } from "./api";
import {
  blocksToPatches,
  joinDiffBodies,
  type DiffBlock,
  type DiffPatch,
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

function DiffHighlight({ body }: { body: string }) {
  const lines = body.replace(/\n$/, "").split("\n");
  return (
    <pre className="diff-panel-pre">
      <code>
        {lines.map((line, i) => {
          let cls = "diff-line";
          if (line.startsWith("+++") || line.startsWith("---")) {
            cls += " diff-file";
          } else if (line.startsWith("+")) {
            cls += " diff-add";
          } else if (line.startsWith("-")) {
            cls += " diff-del";
          } else if (line.startsWith("@@")) {
            cls += " diff-hunk";
          }
          return (
            <span key={i} className={cls}>
              {line}
              {"\n"}
            </span>
          );
        })}
      </code>
    </pre>
  );
}

type Props = {
  blocks: DiffBlock[];
  workspaceEnabled?: boolean;
  workspaceName?: string | null;
  onNotice?: (message: string) => void;
  onApplied?: (result: ApplyDiffResult) => void;
};

export function DiffPanel({
  blocks,
  workspaceEnabled = false,
  workspaceName,
  onNotice,
  onApplied,
}: Props) {
  const patches = useMemo(() => blocksToPatches(blocks), [blocks]);
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(patches.map((p) => [p.path, true])),
  );
  const [applying, setApplying] = useState(false);
  const [applyingPath, setApplyingPath] = useState<string | null>(null);

  if (!blocks.length) return null;

  async function copyOne(patch: DiffPatch) {
    const ok = await copyText(patch.unified_diff);
    onNotice?.(
      ok
        ? `Diff copiado${patch.path ? `: ${patch.path}` : ""}.`
        : "Falha ao copiar.",
    );
  }

  async function copyAll() {
    const ok = await copyText(joinDiffBodies(blocks));
    onNotice?.(
      ok ? `${blocks.length} diff(s) copiado(s).` : "Falha ao copiar.",
    );
  }

  async function applyPatches(selected: DiffPatch[]) {
    if (!workspaceEnabled) {
      onNotice?.("Defina WORKSPACE_ROOT no .env e reinicie o backend.");
      return;
    }
    if (!selected.length) {
      onNotice?.("Nenhum arquivo no diff para aplicar.");
      return;
    }
    const label = workspaceName || "WORKSPACE_ROOT";
    const names = selected.map((p) => p.path).join(", ");
    const okConfirm = window.confirm(
      `Aplicar em «${label}»:\n${names}\n\nBackups .bak serão criados. Continuar?`,
    );
    if (!okConfirm) return;
    setApplying(true);
    try {
      const result = await applyWorkspaceDiffs(selected);
      const fails = result.results.filter((r) => !r.ok);
      if (fails.length === 0) {
        onNotice?.(`Aplicados ${result.applied} arquivo(s) no workspace.`);
      } else {
        onNotice?.(
          `Aplicados ${result.applied}; falhas: ${fails
            .map((f) => `${f.path || "?"}: ${f.error || "erro"}`)
            .join(" · ")}`,
        );
      }
      if (result.applied > 0) {
        onApplied?.(result);
      }
    } catch (err) {
      onNotice?.(err instanceof Error ? err.message : "Falha ao aplicar diffs.");
    } finally {
      setApplying(false);
      setApplyingPath(null);
    }
  }

  async function applyAll() {
    setApplyingPath(null);
    await applyPatches(patches);
  }

  async function applyOne(patch: DiffPatch) {
    setApplyingPath(patch.path);
    await applyPatches([patch]);
  }

  function toggle(path: string) {
    setOpen((prev) => ({ ...prev, [path]: !prev[path] }));
  }

  return (
    <aside className="diff-panel" aria-label="Diffs sugeridos">
      <div className="diff-panel-head">
        <div>
          <strong>Diffs sugeridos</strong>
          <p className="diff-panel-note">
            Sugestão até você confirmar. Aplique um arquivo ou todos.
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
            disabled={!workspaceEnabled || applying || patches.length === 0}
            title={
              workspaceEnabled
                ? "Grava patches em WORKSPACE_ROOT (com .bak)"
                : "Configure WORKSPACE_ROOT no .env"
            }
            onClick={() => void applyAll()}
          >
            {applying && !applyingPath ? "Aplicando…" : "Aplicar todos"}
          </button>
        </div>
      </div>
      <ul className="diff-panel-list">
        {patches.map((patch, index) => {
          const label = patch.path || `Bloco ${index + 1}`;
          const isOpen = open[patch.path] !== false;
          const busy = applying && applyingPath === patch.path;
          return (
            <li key={`${patch.path}-${index}`} className="diff-panel-item">
              <div className="diff-panel-item-bar">
                <button
                  type="button"
                  className="btn-link diff-toggle"
                  aria-expanded={isOpen}
                  onClick={() => toggle(patch.path)}
                >
                  {isOpen ? "▾" : "▸"} {label}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void copyOne(patch)}
                >
                  Copiar
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!workspaceEnabled || applying || !patch.path}
                  title="Aplicar só este arquivo (com confirmação)"
                  onClick={() => void applyOne(patch)}
                >
                  {busy ? "Aplicando…" : "Aplicar"}
                </button>
              </div>
              {isOpen ? <DiffHighlight body={patch.unified_diff} /> : null}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
