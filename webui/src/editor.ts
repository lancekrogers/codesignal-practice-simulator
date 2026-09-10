import * as monaco from "monaco-editor/editor/editor.api";
import { conf, language } from "monaco-editor/languages/definitions/python/python";
import "monaco-editor/editor/contrib/cursorUndo/browser/cursorUndo";
import "monaco-editor/editor/contrib/find/browser/findController";
import "monaco-editor/editor/contrib/folding/browser/folding";
import "monaco-editor/editor/contrib/indentation/browser/indentation";
import "monaco-editor/editor/contrib/parameterHints/browser/parameterHints";
import "monaco-editor/editor/contrib/suggest/browser/suggestController";
import type { ShellElements } from "./views";
import { createDialogFocusTrap } from "./a11y";

export type EditorWorkerUrls = {
  editor: string;
  language: string;
};

export type EditorPreferences = {
  version: 1;
  theme: "vs-dark" | "vs-light";
  fontSize: number;
  tabSize: 2 | 4 | 8;
  minimap: boolean;
  wordWrap: boolean;
  autoClosingBrackets: boolean;
};

export type EditorHandle = {
  getValue(): string;
  setValue(value: string): void;
  setReadOnly(readOnly: boolean): void;
  dispose(): void;
};

export const EDITOR_PREFERENCES_KEY = "simulator-editor-preferences";

const DEFAULT_PREFERENCES: EditorPreferences = {
  version: 1,
  theme: "vs-dark",
  fontSize: 14,
  tabSize: 4,
  minimap: false,
  wordWrap: false,
  autoClosingBrackets: true,
};

export function initializeEditor(
  elements: ShellElements,
  source: string,
  workerUrls: EditorWorkerUrls,
  onChange?: (value: string) => void,
  onFailure?: () => void,
): EditorHandle {
  const workers = configureWorkers(workerUrls, onFailure);
  try {
    registerPython();
    registerCompletions();
    const preferences = loadEditorPreferences();
    monaco.editor.setTheme(preferences.theme);
    const model = monaco.editor.createModel(source, "python");
    const editor = monaco.editor.create(elements.editor, {
      model,
      automaticLayout: true,
      ariaLabel: "Python source editor",
      ...editorOptions(preferences),
      readOnly: false,
    });
    model.onDidChangeContent(() => onChange?.(model.getValue()));
    const settings = createSettingsDialog(
      elements.settingsButton,
      preferences,
      (next) => {
        persistEditorPreferences(next);
        monaco.editor.setTheme(next.theme);
        editor.updateOptions(editorOptions(next));
      },
    );
    return {
      getValue: () => model.getValue(),
      setValue: (value) => model.setValue(value),
      setReadOnly: (readOnly) => editor.updateOptions({ readOnly }),
      dispose: () => {
        workers.dispose();
        settings.dispose();
        editor.dispose();
        model.dispose();
      },
    };
  } catch (error) {
    workers.dispose();
    throw error;
  }
}

export function loadEditorPreferences(): EditorPreferences {
  try {
    const stored = window.localStorage.getItem(EDITOR_PREFERENCES_KEY);
    if (!stored) return { ...DEFAULT_PREFERENCES };
    const parsed: unknown = JSON.parse(stored);
    return isEditorPreferences(parsed) ? parsed : { ...DEFAULT_PREFERENCES };
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

function persistEditorPreferences(preferences: EditorPreferences): void {
  if (!isEditorPreferences(preferences)) return;
  try {
    window.localStorage.setItem(
      EDITOR_PREFERENCES_KEY,
      JSON.stringify(preferences),
    );
  } catch {
    // The editor remains usable when browser storage is unavailable.
  }
}

function editorOptions(
  preferences: EditorPreferences,
): monaco.editor.IStandaloneEditorConstructionOptions {
  return {
    lineNumbers: "on",
    fontSize: preferences.fontSize,
    insertSpaces: true,
    tabSize: preferences.tabSize,
    minimap: { enabled: preferences.minimap },
    wordWrap: preferences.wordWrap ? "on" : "off",
    autoClosingBrackets: preferences.autoClosingBrackets ? "always" : "never",
    autoIndent: "full",
    bracketPairColorization: { enabled: true },
    quickSuggestions: true,
    suggestOnTriggerCharacters: true,
  };
}

function isEditorPreferences(value: unknown): value is EditorPreferences {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const candidate = value as Record<string, unknown>;
  const keys = Object.keys(candidate).sort().join(",");
  if (
    keys !==
    "autoClosingBrackets,fontSize,minimap,tabSize,theme,version,wordWrap"
  ) {
    return false;
  }
  return (
    candidate.version === 1 &&
    (candidate.theme === "vs-dark" || candidate.theme === "vs-light") &&
    Number.isInteger(candidate.fontSize) &&
    Number(candidate.fontSize) >= 12 &&
    Number(candidate.fontSize) <= 22 &&
    typeof candidate.tabSize === "number" &&
    [2, 4, 8].includes(candidate.tabSize) &&
    typeof candidate.minimap === "boolean" &&
    typeof candidate.wordWrap === "boolean" &&
    typeof candidate.autoClosingBrackets === "boolean"
  );
}

type SettingsDialog = {
  dispose(): void;
};

function createSettingsDialog(
  button: HTMLButtonElement,
  initial: EditorPreferences,
  onApply: (preferences: EditorPreferences) => void,
): SettingsDialog {
  const dialog = document.createElement("dialog");
  dialog.className = "editor-settings";
  dialog.setAttribute("aria-labelledby", "editor-settings-title");
  const title = document.createElement("h2");
  title.id = "editor-settings-title";
  title.textContent = "Editor settings";
  const parts = createSettingsForm(initial);
  const { form, error, apply, cancel } = parts;
  dialog.append(title, form);
  const focus = createDialogFocusTrap(dialog, { initialFocus: apply });
  cancel.addEventListener("click", () => focus.close());
  const open = (): void => focus.open(button);
  const submit = submitSettings(form, error, focus.close, onApply);
  button.addEventListener("click", open);
  form.addEventListener("submit", submit);
  button.parentElement?.parentElement?.append(dialog);
  return {
    dispose: () => {
      button.removeEventListener("click", open);
      form.removeEventListener("submit", submit);
      focus.close();
      focus.dispose();
      dialog.remove();
    },
  };
}

function createSettingsForm(initial: EditorPreferences): {
  form: HTMLFormElement;
  error: HTMLElement;
  apply: HTMLButtonElement;
  cancel: HTMLButtonElement;
} {
  const form = document.createElement("form");
  form.method = "dialog";
  form.append(
    selectField("Theme", "theme", [["vs-dark", "Dark"], ["vs-light", "Light"]]),
    selectField("Font size", "fontSize", [...fontSizes()].map((size) => [
      String(size),
      `${size}px`,
    ])),
    selectField("Tab size", "tabSize", [
      ["2", "2 spaces"],
      ["4", "4 spaces"],
      ["8", "8 spaces"],
    ]),
    checkboxField("Show minimap", "minimap"),
    checkboxField("Wrap long lines", "wordWrap"),
    checkboxField("Auto-close brackets", "autoClosingBrackets"),
  );
  const error = document.createElement("p");
  error.className = "settings-error";
  error.setAttribute("role", "alert");
  const actions = document.createElement("div");
  actions.className = "settings-actions";
  const cancel = settingsButton("Cancel", "secondary");
  const apply = settingsButton("Apply settings", "primary");
  apply.type = "submit";
  actions.append(cancel, apply);
  form.append(error, actions);
  setFormPreferences(form, initial);
  return { form, error, apply, cancel };
}

function submitSettings(
  form: HTMLFormElement,
  error: HTMLElement,
  close: () => void,
  onApply: (preferences: EditorPreferences) => void,
): (event: SubmitEvent) => void {
  return (event) => {
    event.preventDefault();
    const next = readFormPreferences(form);
    if (!next) {
      error.textContent = "Choose valid values before applying settings.";
      return;
    }
    error.textContent = "";
    onApply(next);
    close();
  };
}

function fontSizes(): number[] {
  return Array.from({ length: 11 }, (_, index) => index + 12);
}

function selectField(
  labelText: string,
  name: string,
  options: string[][],
): HTMLLabelElement {
  const label = document.createElement("label");
  label.textContent = labelText;
  const select = document.createElement("select");
  select.name = name;
  select.id = `editor-setting-${name}`;
  options.forEach(([value, text]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.append(option);
  });
  label.htmlFor = select.id;
  label.append(select);
  return label;
}

function checkboxField(labelText: string, name: string): HTMLLabelElement {
  const label = document.createElement("label");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = name;
  input.id = `editor-setting-${name}`;
  label.htmlFor = input.id;
  label.append(input, document.createTextNode(labelText));
  return label;
}

function setFormPreferences(
  form: HTMLFormElement,
  preferences: EditorPreferences,
): void {
  const theme = form.elements.namedItem("theme") as HTMLSelectElement;
  const fontSize = form.elements.namedItem("fontSize") as HTMLSelectElement;
  const tabSize = form.elements.namedItem("tabSize") as HTMLSelectElement;
  theme.value = preferences.theme;
  fontSize.value = String(preferences.fontSize);
  tabSize.value = String(preferences.tabSize);
  for (const name of ["minimap", "wordWrap", "autoClosingBrackets"]) {
    const input = form.elements.namedItem(name) as HTMLInputElement;
    input.checked = preferences[name];
  }
}

function readFormPreferences(form: HTMLFormElement): EditorPreferences | null {
  const theme = form.elements.namedItem("theme") as HTMLSelectElement;
  const fontSize = form.elements.namedItem("fontSize") as HTMLSelectElement;
  const tabSize = form.elements.namedItem("tabSize") as HTMLSelectElement;
  const candidate = {
    version: 1 as const,
    theme: theme.value,
    fontSize: Number(fontSize.value),
    tabSize: Number(tabSize.value),
    minimap: (form.elements.namedItem("minimap") as HTMLInputElement).checked,
    wordWrap: (form.elements.namedItem("wordWrap") as HTMLInputElement).checked,
    autoClosingBrackets: (form.elements.namedItem(
      "autoClosingBrackets",
    ) as HTMLInputElement).checked,
  };
  return isEditorPreferences(candidate) ? candidate : null;
}

function settingsButton(
  label: string,
  className: string,
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  return button;
}

function configureWorkers(
  urls: EditorWorkerUrls,
  onFailure?: () => void,
): { dispose(): void } {
  const environment = ((globalThis as any).MonacoEnvironment || {}) as Record<
    string,
    unknown
  >;
  let active = true;
  const listeners = new Map<Worker, EventListener>();
  environment.getWorker = (_moduleId: string, label: string) => {
    const worker = new Worker(workerUrl(label === "python" ? urls.language : urls.editor), {
      type: "module",
      name: `simulator-${label || "editor"}-worker`,
    });
    if (onFailure) {
      const listener: EventListener = () => {
        if (active) onFailure();
      };
      worker.addEventListener("error", listener, { once: true });
      listeners.set(worker, listener);
    }
    return worker;
  };
  environment.getWorkerUrl = (_moduleId: string, label: string) =>
    workerUrl(label === "python" ? urls.language : urls.editor);
  (globalThis as any).MonacoEnvironment = environment;
  return {
    dispose: () => {
      active = false;
      listeners.forEach((listener, worker) => {
        worker.removeEventListener("error", listener);
      });
      listeners.clear();
    },
  };
}

function workerUrl(value: string): string {
  const url = new URL(value, window.location.origin);
  if (url.origin !== window.location.origin || !url.pathname.startsWith("/")) {
    throw new Error("worker URL is not same-origin");
  }
  return url.href;
}

function registerPython(): void {
  if (!monaco.languages.getLanguages().some((entry) => entry.id === "python")) {
    monaco.languages.register({
      id: "python",
      extensions: [".py"],
      aliases: ["Python", "py"],
    });
  }
  monaco.languages.setLanguageConfiguration("python", conf);
  monaco.languages.setMonarchTokensProvider("python", language);
}

let completionProvider: { dispose(): void } | null = null;

function registerCompletions(): void {
  if (completionProvider) return;
  completionProvider = monaco.languages.registerCompletionItemProvider("python", {
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = new monaco.Range(
        position.lineNumber,
        word.startColumn,
        position.lineNumber,
        word.endColumn,
      );
      const suggestions = ["def", "class", "for", "if", "import", "print", "return"];
      return {
        suggestions: suggestions.map((label) => ({
          label,
          kind: monaco.languages.CompletionItemKind.Keyword,
          insertText: label,
          range,
        })),
      };
    },
  });
}
