import { useEffect, useState } from "react";
import {
  fetchWorkspaceTree,
  readWorkspaceFile,
  type WorkspaceTreeEntry,
} from "./api";

type Props = {
  enabled: boolean;
  onAddContext: (path: string) => void;
};

export function WorkspacePanel({ enabled, onAddContext }: Props) {
  const [prefix, setPrefix] = useState("");
  const [entries, setEntries] = useState<WorkspaceTreeEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [previewBusy, setPreviewBusy] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    void fetchWorkspaceTree(prefix)
      .then((list) => {
        if (!cancelled) setEntries(list);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setEntries([]);
          setError(err instanceof Error ? err.message : "Falha ao listar");
        }
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, prefix]);

  if (!enabled) return null;

  async function openFile(path: string) {
    setPreviewPath(path);
    setPreviewBusy(true);
    setPreview("");
    try {
      const data = await readWorkspaceFile(path);
      setPreview(data.content || "");
    } catch (err) {
      setPreview(
        err instanceof Error ? err.message : "Não foi possível ler o arquivo.",
      );
    } finally {
      setPreviewBusy(false);
    }
  }

  const parent =
    prefix.includes("/")
      ? prefix.split("/").slice(0, -1).join("/")
      : "";

  // Immediate children of current prefix
  const visible = entries.filter((e) => {
    const p = e.path.replace(/\/$/, "");
    if (!prefix) {
      return !p.includes("/");
    }
    const pref = `${prefix}/`;
    if (!p.startsWith(pref)) return false;
    const rest = p.slice(pref.length);
    return rest.length > 0 && !rest.includes("/");
  });

  return (
    <aside className="workspace-panel" aria-label="Workspace">
      <div className="workspace-panel-head">
        <strong>Workspace</strong>
        <span className="meta-line">
          {prefix ? `${prefix}/` : "(raiz)"}
          {busy ? " · …" : ""}
        </span>
      </div>
      {prefix ? (
        <button
          type="button"
          className="btn-link"
          onClick={() => setPrefix(parent)}
        >
          ← subir
        </button>
      ) : null}
      {error ? <p className="error-text">{error}</p> : null}
      <ul className="workspace-tree">
        {visible.length === 0 && !busy ? (
          <li className="at-file-empty">Nada nesta pasta</li>
        ) : (
          visible.map((e) => {
            const isDir = e.kind === "dir" || e.path.endsWith("/");
            const label = e.path.replace(/\/$/, "").split("/").pop() || e.path;
            return (
              <li key={e.path}>
                <button
                  type="button"
                  className="workspace-tree-item"
                  onClick={() => {
                    if (isDir) {
                      setPrefix(e.path.replace(/\/$/, ""));
                    } else {
                      void openFile(e.path);
                    }
                  }}
                >
                  <span className="workspace-kind">{isDir ? "dir" : "file"}</span>{" "}
                  {label}
                  {isDir ? "/" : ""}
                </button>
                <button
                  type="button"
                  className="btn-link"
                  title={isDir ? "Adicionar pasta ao contexto @" : "Adicionar arquivo @"}
                  onClick={() =>
                    onAddContext(isDir ? e.path.replace(/\/?$/, "/") : e.path)
                  }
                >
                  +@
                </button>
              </li>
            );
          })
        )}
      </ul>
      {previewPath ? (
        <div className="workspace-preview">
          <div className="workspace-preview-bar">
            <code>{previewPath}</code>
            <button
              type="button"
              className="btn-link"
              onClick={() => onAddContext(previewPath)}
            >
              +@ contexto
            </button>
            <button
              type="button"
              className="btn-link"
              onClick={() => {
                setPreviewPath(null);
                setPreview("");
              }}
            >
              fechar
            </button>
          </div>
          <pre className="workspace-preview-pre">
            {previewBusy ? "Lendo…" : preview}
          </pre>
        </div>
      ) : null}
    </aside>
  );
}
