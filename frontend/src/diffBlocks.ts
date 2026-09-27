/** Extract fenced ```diff / ```patch blocks from assistant markdown. */

export type DiffBlock = {
  id: string;
  lang: "diff" | "patch";
  body: string;
  files: string[];
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

export function blocksToPatches(
  blocks: DiffBlock[],
): { path: string; unified_diff: string }[] {
  return blocks.map((b) => ({
    path: b.files[0] || "",
    unified_diff: b.body,
  }));
}
