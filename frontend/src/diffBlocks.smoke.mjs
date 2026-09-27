/** Smoke: multi-file unified diff split (mirrors diffBlocks.ts). Run: node src/diffBlocks.smoke.mjs */

function extractFiles(body) {
  const files = [];
  const seen = new Set();
  const push = (raw) => {
    let p = raw.trim();
    if (!p || p === "/dev/null") return;
    if (p.startsWith("b/") || p.startsWith("a/")) p = p.slice(2);
    if (seen.has(p)) return;
    seen.add(p);
    files.push(p);
  };
  for (const m of body.matchAll(/^\+\+\+\s+(\S+)/gm)) push(m[1]);
  if (files.length === 0) {
    for (const m of body.matchAll(/^---\s+(\S+)/gm)) push(m[1]);
  }
  return files;
}

function splitUnifiedDiff(body) {
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
      .map((chunk) => ({
        path: extractFiles(chunk)[0] || "",
        unified_diff: chunk,
      }))
      .filter((p) => p.path || p.unified_diff.trim());
  }
  return [{ path: extractFiles(body)[0] || "", unified_diff: normalized }];
}

const multi = `diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1 @@
-a = 1
+a = 2
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1 +1 @@
-b = 1
+b = 2
`;

const parts = splitUnifiedDiff(multi);
if (parts.length !== 2) throw new Error(`expected 2 parts, got ${parts.length}`);
if (parts[0].path !== "a.py" || parts[1].path !== "b.py") {
  throw new Error(`bad paths: ${parts.map((p) => p.path).join(",")}`);
}
console.log("diffBlocks.smoke ok", parts.map((p) => p.path).join(", "));
