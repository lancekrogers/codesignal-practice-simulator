import * as monaco from "monaco-editor/editor/editor.api";
import { conf, language } from "monaco-editor/languages/definitions/python/python";
import "monaco-editor/editor/contrib/cursorUndo/browser/cursorUndo";
import "monaco-editor/editor/contrib/find/browser/findController";
import "monaco-editor/editor/contrib/folding/browser/folding";
import "monaco-editor/editor/contrib/indentation/browser/indentation";
import "monaco-editor/editor/contrib/parameterHints/browser/parameterHints";
import "monaco-editor/editor/contrib/suggest/browser/suggestController";
import type { ShellElements } from "./views";

export type EditorWorkerUrls = {
  editor: string;
  language: string;
};

export type EditorHandle = {
  getValue(): string;
  dispose(): void;
};

export function initializeEditor(
  elements: ShellElements,
  source: string,
  workerUrls: EditorWorkerUrls,
  onChange?: () => void,
): EditorHandle {
  configureWorkers(workerUrls);
  registerPython();
  const model = monaco.editor.createModel(source, "python");
  const editor = monaco.editor.create(elements.editor, {
    model,
    automaticLayout: true,
    ariaLabel: "Python source editor",
    fontSize: 14,
    insertSpaces: true,
    tabSize: 4,
    minimap: { enabled: false },
    readOnly: false,
    theme: "vs-dark",
    wordWrap: "off",
  });
  model.onDidChangeContent(() => onChange?.());
  registerCompletions();
  return {
    getValue: () => model.getValue(),
    dispose: () => {
      editor.dispose();
      model.dispose();
    },
  };
}

function configureWorkers(urls: EditorWorkerUrls): void {
  const environment = ((globalThis as any).MonacoEnvironment || {}) as Record<
    string,
    unknown
  >;
  environment.getWorker = (_moduleId: string, label: string) =>
    new Worker(workerUrl(label === "python" ? urls.language : urls.editor), {
      type: "module",
      name: `simulator-${label || "editor"}-worker`,
    });
  environment.getWorkerUrl = (_moduleId: string, label: string) =>
    workerUrl(label === "python" ? urls.language : urls.editor);
  (globalThis as any).MonacoEnvironment = environment;
}

function workerUrl(value: string): string {
  const url = new URL(value, window.location.origin);
  if (url.origin !== window.location.origin || !url.pathname.startsWith("/")) {
    throw new Error("worker URL is not same-origin");
  }
  return url.href;
}

function registerPython(): void {
  if (monaco.languages.getLanguages().some((entry) => entry.id === "python")) return;
  monaco.languages.register({
    id: "python",
    extensions: [".py"],
    aliases: ["Python", "py"],
  });
  monaco.languages.setLanguageConfiguration("python", conf);
  monaco.languages.setMonarchTokensProvider("python", language);
}

function registerCompletions(): void {
  monaco.languages.registerCompletionItemProvider("python", {
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
