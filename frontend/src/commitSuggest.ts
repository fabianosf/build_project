/** Build a commit message draft from git status / diff --stat output (no git write). */

function parseChangedPaths(statusOut: string): string[] {
  const paths: string[] = [];
  const seen = new Set<string>();
  for (const raw of statusOut.split("\n")) {
    const line = raw.trimEnd();
    if (!line || line.startsWith("##")) continue;
    // porcelain short: XY path  or  XY orig -> path
    const m = /^(?:[ MADRCU?!]{1,2})\s+(.+?)(?:\s+->\s+(.+))?$/.exec(
      line.trim(),
    );
    if (!m) continue;
    const path = (m[2] || m[1] || "").trim();
    if (!path || seen.has(path)) continue;
    seen.add(path);
    paths.push(path);
  }
  return paths;
}

function guessPrefix(paths: string[]): string {
  const joined = paths.join(" ").toLowerCase();
  if (/\b(test|spec)\b/.test(joined)) return "test";
  if (/\b(readme|docs?)\b/.test(joined)) return "docs";
  if (/\b(fix|style)\b/.test(joined)) return "style";
  if (paths.length === 1 && /\.(md|txt)$/i.test(paths[0])) return "docs";
  if (/\b(fix|bug)\b/.test(joined)) return "fix";
  return "chore";
}

export function buildCommitSuggestion(
  statusOut: string,
  diffStatOut = "",
): string {
  const paths = parseChangedPaths(statusOut);
  const prefix = guessPrefix(paths);
  const focus =
    paths.length === 0
      ? "update workspace"
      : paths.length === 1
        ? paths[0]
        : paths.length <= 3
          ? paths.join(", ")
          : `${paths.slice(0, 2).join(", ")} (+${paths.length - 2})`;
  const lines = [`${prefix}: ${focus}`, ""];
  if (paths.length) {
    lines.push("Changed:");
    for (const p of paths.slice(0, 20)) {
      lines.push(`- ${p}`);
    }
    if (paths.length > 20) {
      lines.push(`- … +${paths.length - 20} more`);
    }
  }
  const stat = diffStatOut.trim();
  if (stat) {
    lines.push("", "---", stat.split("\n").slice(0, 30).join("\n"));
  }
  return lines.join("\n").trim() + "\n";
}
