import type {
  AttemptStatus,
  PracticeResult,
  ScoreSummary,
} from "./state";

export type OutputElements = HTMLElement & {
  render(score: ScoreSummary | null, status: AttemptStatus, practice: PracticeResult | null): void;
};

const MAX_OUTPUT_BYTES = 4096;

export function createOutputPane(
  score: ScoreSummary | null,
  status: AttemptStatus,
  practice: PracticeResult | null = null,
): OutputElements {
  const pane = document.createElement("aside");
  pane.className = "output-drawer";
  pane.dataset.testid = "output-drawer";
  pane.setAttribute("aria-labelledby", "output-title");
  pane.append(createHeading(), document.createElement("div"));
  const output = pane.lastElementChild as HTMLElement;
  output.className = "output-results";
  const result = Object.assign(pane, {
    render: (nextScore: ScoreSummary | null, nextStatus: AttemptStatus, nextPractice: PracticeResult | null) =>
      renderResults(output, nextScore, nextStatus, nextPractice),
  }) as OutputElements;
  result.render(score, status, practice);
  return result;
}

function createHeading(): HTMLElement {
  const heading = document.createElement("div");
  heading.className = "pane-heading";
  const title = document.createElement("h2");
  title.id = "output-title";
  title.textContent = "Output";
  const limit = document.createElement("span");
  limit.className = "pane-detail";
  limit.textContent = "Bounded preview";
  heading.append(title, limit);
  return heading;
}

function renderResults(
  output: HTMLElement,
  score: ScoreSummary | null,
  status: AttemptStatus,
  practice: PracticeResult | null,
): void {
  output.replaceChildren();
  if (!score) {
    addText(output, status === "expired"
      ? "This attempt has expired. The server snapshot is final for this view."
      : status === "abandoned"
        ? "This attempt was ended before submission. No final result was recorded."
        : "Run local practice checks to see bounded per-level results.");
    return;
  }
  const summary = document.createElement("p");
  summary.className = "output-copy";
  summary.textContent = `${status === "submitted" ? "Final result" : "Practice result"} · ` +
    `Passed levels: ${score.passed_levels} of ${score.levels.length}.`;
  output.append(summary);
  const list = document.createElement("ol");
  list.className = "practice-results";
  score.levels.forEach((level) => {
    const evidence = practice?.levels.find((item) => item.level === level.level);
    const item = document.createElement("li");
    item.className = `practice-result practice-${level.outcome}`;
    const label = document.createElement("strong");
    label.textContent = `Level ${level.level}: ${labelFor(level.outcome)}`;
    item.append(label);
    if (evidence?.candidate_output) addBlock(item, "Candidate output", evidence.candidate_output);
    if (evidence?.candidate_error) addBlock(item, "Candidate error", evidence.candidate_error);
    if (!evidence && level.outcome === "failed") {
      addText(item, "This local practice group did not pass.");
    }
    if (level.outcome === "error" && !evidence?.candidate_error) {
      addText(item, "The local practice check was unavailable.");
    }
    list.append(item);
  });
  output.append(list);
}

function addBlock(parent: HTMLElement, label: string, value: string): void {
  const heading = document.createElement("span");
  heading.className = "output-label";
  heading.textContent = label;
  const block = document.createElement("pre");
  block.textContent = normalizeOutput(value);
  parent.append(heading, block);
}

function addText(parent: HTMLElement, value: string): void {
  const copy = document.createElement("p");
  copy.className = "output-copy";
  copy.textContent = value;
  parent.append(copy);
}

function normalizeOutput(value: string): string {
  const encoded = new TextEncoder().encode(value);
  if (encoded.length <= MAX_OUTPUT_BYTES) return value;
  const marker = "\n[output truncated]";
  let prefix = encoded.slice(0, MAX_OUTPUT_BYTES - new TextEncoder().encode(marker).length);
  const decoder = new TextDecoder("utf-8", { fatal: true });
  while (prefix.length > 0) {
    try {
      return decoder.decode(prefix) + marker;
    } catch {
      prefix = prefix.slice(0, -1);
    }
  }
  return marker;
}

function labelFor(outcome: string): string {
  if (outcome === "passed") return "Passed";
  if (outcome === "failed") return "Needs work";
  return "Unavailable";
}
