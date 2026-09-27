/** Pick code-relevant files from a directory FileList (webkitdirectory). */

const SKIP_DIR_PARTS = new Set([
  "node_modules",
  ".git",
  "dist",
  "build",
  ".venv",
  "venv",
  "__pycache__",
  ".next",
  "coverage",
  ".turbo",
  "vendor",
  "target",
  ".idea",
  ".cursor",
]);

const CODE_EXT = new Set([
  ".py",
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
  ".go",
  ".rs",
  ".java",
  ".kt",
  ".md",
  ".json",
  ".toml",
  ".yml",
  ".yaml",
  ".css",
  ".scss",
  ".html",
  ".sql",
  ".sh",
  ".env.example",
  ".txt",
  ".csv",
]);

const PRIORITY_NAMES = new Set([
  "package.json",
  "package-lock.json",
  "requirements.txt",
  "pyproject.toml",
  "cargo.toml",
  "go.mod",
  "readme.md",
  "dockerfile",
  "tsconfig.json",
  "vite.config.ts",
  "vite.config.js",
  "manage.py",
  "settings.py",
]);

export const FOLDER_MAX_FILES = 16;
export const FOLDER_MAX_FILE_BYTES = 200 * 1024;

function relPath(file: File): string {
  const anyFile = file as File & { webkitRelativePath?: string };
  const rel = (anyFile.webkitRelativePath || file.name).replace(/\\/g, "/");
  // Drop the root folder segment so names stay useful: src/App.tsx
  const parts = rel.split("/").filter(Boolean);
  if (parts.length > 1) return parts.slice(1).join("/");
  return parts[0] || file.name;
}

function shouldSkip(rel: string): boolean {
  const parts = rel.split("/");
  for (const p of parts) {
    if (SKIP_DIR_PARTS.has(p)) return true;
    if (p.startsWith(".") && p !== ".env.example") {
      // allow .env.example only at basename
      if (p !== parts[parts.length - 1]) return true;
    }
  }
  return false;
}

function isCodeFile(rel: string): boolean {
  const base = rel.split("/").pop()?.toLowerCase() || "";
  if (PRIORITY_NAMES.has(base)) return true;
  const dot = base.lastIndexOf(".");
  if (dot < 0) return false;
  const ext = base.slice(dot);
  return CODE_EXT.has(ext) || base.endsWith(".env.example");
}

function priorityScore(rel: string): number {
  const base = rel.split("/").pop()?.toLowerCase() || "";
  if (PRIORITY_NAMES.has(base)) return 0;
  const depth = rel.split("/").length;
  return 10 + depth;
}

export type FolderPickResult = {
  files: File[];
  skipped: number;
  truncated: boolean;
  rootLabel: string;
};

export function pickFolderFiles(list: FileList | null): FolderPickResult {
  if (!list?.length) {
    return { files: [], skipped: 0, truncated: false, rootLabel: "" };
  }
  const all = Array.from(list);
  const rootLabel =
    (all[0] as File & { webkitRelativePath?: string }).webkitRelativePath?.split(
      "/",
    )[0] || "pasta";

  const candidates: { file: File; rel: string; score: number }[] = [];
  let skipped = 0;
  for (const file of all) {
    const rel = relPath(file);
    if (shouldSkip(rel) || !isCodeFile(rel)) {
      skipped += 1;
      continue;
    }
    if (file.size > FOLDER_MAX_FILE_BYTES) {
      skipped += 1;
      continue;
    }
    candidates.push({ file, rel, score: priorityScore(rel) });
  }
  candidates.sort((a, b) => a.score - b.score || a.rel.localeCompare(b.rel));
  const truncated = candidates.length > FOLDER_MAX_FILES;
  const files = candidates.slice(0, FOLDER_MAX_FILES).map((c) => {
    // Preserve relative path as the attachment display name
    const renamed = new File([c.file], c.rel, { type: c.file.type });
    return renamed;
  });
  return { files, skipped, truncated, rootLabel };
}
