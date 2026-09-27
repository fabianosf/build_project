/**
 * Guards against double-recording the same execution (e.g. persist inside a
 * setState updater under React StrictMode calling the updater twice).
 */
import { describe, expect, it } from "vitest";
import {
  appendTelemetryRun,
  type TaskTelemetry,
} from "./historyStore";

function task(partial: Partial<TaskTelemetry> = {}): TaskTelemetry {
  return {
    suggestedId: "a",
    chosenId: "a",
    msSuggest: 10,
    msRun: 20,
    tokensApprox: 100,
    corrected: false,
    contextCharsBefore: 1000,
    contextCharsAfter: 1000,
    contextCompacted: false,
    ...partial,
  };
}

describe("appendTelemetryRun", () => {
  it("keeps a single task when the same metrics are appended twice", () => {
    const once = task({ tokensApprox: 50 });
    const runs = appendTelemetryRun([], once);
    const again = appendTelemetryRun(runs, { ...once });
    expect(again).toHaveLength(1);
    expect(again[0].tokensApprox).toBe(50);
  });

  it("records two tasks when metrics differ (two real executions)", () => {
    const first = task({ tokensApprox: 50, msRun: 20 });
    const second = task({
      tokensApprox: 80,
      msRun: 40,
      corrected: true,
      chosenId: "b",
    });
    const runs = appendTelemetryRun(appendTelemetryRun([], first), second);
    expect(runs).toHaveLength(2);
    expect(runs[0].tokensApprox).toBe(50);
    expect(runs[1].tokensApprox).toBe(80);
  });
});
