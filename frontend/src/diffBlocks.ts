/** Extract fenced ```diff / ```patch blocks from assistant markdown. */

export type DiffBlock = {
  id: string;
  lang: "diff" | "patch";
  body: string;
  files: string[];
};

export type DiffPatch = {
  path: string;
  unified_diff: string;
};

const FENCE_RE = /```(diff|patch)\s*\n([\s\S]*?)```/gi;

function extractFiles(body: string): string[] {
  const files: string[] = [];
  const seen = new Set<string>();

  const push = (raw: string) => {
    let p = raw.trim();
    if (!p || p === "/dev/null") return;
    if (p.startsWith("b/") || p.startsWith("a/")) p = p.slice(2);
    if (seen.has(p)) return;
    seen.add(p);
    files.push(p);
  };

  for (const m of body.matchAll(/^\+\+\+\s+(\S+)/gm)) {
    push(m[1]);
  }
  if (files.length === 0) {
    for (const m of body.matchAll(/^---\s+(\S+)/gm)) {
      push(m[1]);
    }
  }
  return files;
}

/** Split a unified diff that may contain multiple files into per-file patches. */
export function splitUnifiedDiff(body: string): DiffPatch[] {
  const normalized = body.replace(/\r\n/g, "\n").replace(/\n$/, "") + "\n";
  const gitChunks = normalized
    .split(/(?=^diff --git )/m)
    .map((c) => c.trimEnd() + "\n")
    .filter((c) => c.trim());

  if (
    gitChunks.length > 1 ||
    (gitChunks.length === 1 && gitChunks[0].startsWith("diff --git "))
  ) {
    return gitChunks
      .map((chunk) => {
        const files = extractFiles(chunk);
        return { path: files[0] || "", unified_diff: chunk };
      })
      .filter((p) => p.path || p.unified_diff.trim());
  }

  const fileChunks = normalized
    .split(/(?=^--- )/m)
    .map((c) => c.trimEnd() + "\n")
    .filter((c) => c.trim().startsWith("--- "));

  if (fileChunks.length > 1) {
    return fileChunks
      .map((chunk) => {
        const files = extractFiles(chunk);
        return { path: files[0] || "", unified_diff: chunk };
      })
      .filter((p) => Boolean(p.path));
  }

  const files = extractFiles(body);
  return [
    {
      path: files[0] || "",
      unified_diff: normalized,
    },
  ];
}

export function parseDiffBlocks(markdown: string): DiffBlock[] {
  if (!markdown) return [];
  const out: DiffBlock[] = [];
  let match: RegExpExecArray | null;
  const re = new RegExp(FENCE_RE.source, FENCE_RE.flags);
  let i = 0;
  while ((match = re.exec(markdown)) !== null) {
    const lang = match[1].toLowerCase() as "diff" | "patch";
    const body = match[2].replace(/\n$/, "");
    if (!body.trim()) continue;
    out.push({
      id: `diff-${i++}-${body.length}`,
      lang,
      body,
      files: extractFiles(body),
    });
  }
  return out;
}

export function joinDiffBodies(blocks: DiffBlock[]): string {
  return blocks.map((b) => b.body).join("\n\n");
}

export function blocksToPatches(blocks: DiffBlock[]): DiffPatch[] {
  const out: DiffPatch[] = [];
  const seen = new Set<string>();
  for (const block of blocks) {
    for (const patch of splitUnifiedDiff(block.body)) {
      if (!patch.path) continue;
      const key = `${patch.path}\0${patch.unified_diff}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(patch);
    }
  }
  return out;
}
