import type { ScoreSummary, AttemptStatus } from "./state";

export function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  if (className) result.className = className;
  return result;
}

export function button(label: string, className: string): HTMLButtonElement {
  const result = document.createElement("button");
  result.type = "button";
  result.className = className;
  result.textContent = label;
  return result;
}

export function disabledButton(
  label: string,
  className: string,
): HTMLButtonElement {
  const result = button(label, className);
  result.disabled = true;
  if (["Run Tests", "Reset source", "End attempt", "Restart", "Submit"].includes(label)) {
    result.dataset.mutation = "true";
  }
  return result;
}

export function statusItem(label: string, valueText: string): {
  container: HTMLElement;
  value: HTMLElement;
} {
  const container = element("div", "header-status");
  const labelElement = element("span", "meta-label");
  labelElement.textContent = label;
  const value = element("strong");
  value.textContent = valueText;
  container.append(labelElement, value);
  return { container, value };
}

export function formatCountdown(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainder = safeSeconds % 60;
  if (hours > 0) return `${hours}:${pad(minutes)}:${pad(remainder)}`;
  return `${pad(minutes)}:${pad(remainder)}`;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function terminalEditorMessage(status: AttemptStatus): string {
  if (status === "submitted") return "This attempt is submitted. Editing is unavailable.";
  if (status === "abandoned") return "This attempt was ended. Editing is unavailable.";
  return "This attempt is expired. Editing is unavailable.";
}

export function lifecycleLabel(status: AttemptStatus): string {
  if (status === "active") return "Active";
  if (status === "abandoned") return "Ended";
  return status === "expired" ? "Expired" : "Submitted";
}

export function resultLabel(status: AttemptStatus): string {
  return status === "submitted" ? "Final result" : "Practice result";
}

export function terminalAnnouncement(
  status: AttemptStatus,
  score: ScoreSummary | null,
  source: string | null,
): string {
  const sourceMessage = source === null
    ? "Source is unavailable."
    : "Source remains available.";
  if (status === "expired") {
    return `Attempt expired. ${sourceMessage} Results remain available in read-only mode.`;
  }
  if (status === "abandoned") {
    return `Attempt ended without submission. ${sourceMessage} Saved work remains available in read-only mode.`;
  }
  if (score) {
    return `Final result announced. Passed levels: ${score.passed_levels} of ${score.levels.length}. ${sourceMessage} Results are final and read-only.`;
  }
  return `Attempt submitted. ${sourceMessage} Results are final and read-only.`;
}
