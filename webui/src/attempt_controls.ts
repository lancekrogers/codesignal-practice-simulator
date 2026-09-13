import { focusFirstAction, type Disposable, createLiveRegion } from "./a11y";
import type { ConfirmationDialog } from "./confirmation_dialog";
import type { AttemptState } from "./state";
import type { EditorElements, ShellElements } from "./attempt_types";
import type { LevelNavigation } from "./navigation_view";

export function createControlApi(
  state: AttemptState,
  levelNav: LevelNavigation,
  actions: { setNavigationLevel(level: number): void },
  controls: HTMLButtonElement[],
  mutationControls: HTMLButtonElement[],
  disposables: Disposable[],
  live: ReturnType<typeof createLiveRegion>,
  confirmation: ConfirmationDialog,
  editor: EditorElements,
): Pick<
  ShellElements,
  | "focusInitial"
  | "focusLevel"
  | "refreshLevelStatus"
  | "setNavigationLevel"
  | "setControlsDisabled"
  | "setMutationControlsDisabled"
  | "setActionState"
  | "setOperationBusy"
  | "setResetEnabled"
  | "confirmAction"
  | "destroy"
> {
  const reset = controls.find((control) => control.textContent === "Reset source");
  let operationBusy = false;
  return {
    focusInitial: () => focusFirstAction(levelNav.element),
    focusLevel: (level) => levelNav.focusLevel(level),
    refreshLevelStatus: () => levelNav.refreshStatus(),
    setNavigationLevel: (level) => actions.setNavigationLevel(level),
    setControlsDisabled: (disabled) => setDisabled(controls, disabled),
    setMutationControlsDisabled: (disabled) =>
      setDisabled(mutationControls, disabled),
    setActionState: (action) => {
      setDisabled(
        mutationControls,
        operationBusy || state.session.status !== "active" || action !== "idle",
      );
      setActionLabels(controls, action);
    },
    setOperationBusy: (busy) => {
      operationBusy = busy;
      setDisabled(
        mutationControls,
        operationBusy ||
          state.session.status !== "active" ||
          state.action !== "idle",
      );
    },
    setResetEnabled: (enabled) => setResetEnabled(state, reset, enabled),
    confirmAction: (title, description, label, opener, onConfirm) =>
      confirmation.open(
        opener,
        title,
        description,
        label,
        onConfirm,
      ),
    destroy: () => destroyControls(
      controls,
      disposables,
      editor,
      confirmation,
      live,
    ),
  };
}

function setActionLabels(
  controls: HTMLButtonElement[],
  action: "idle" | "testing" | "submitting",
): void {
  const run = controls.find((control) => control.textContent === "Run Tests" ||
    control.dataset.action === "run");
  const submit = controls.find((control) => control.textContent === "Submit" ||
    control.dataset.action === "submit");
  if (run) {
    run.dataset.action = "run";
    run.textContent = action === "testing" ? "Testing…" : "Run Tests";
  }
  if (submit) {
    submit.dataset.action = "submit";
    submit.textContent = action === "submitting" ? "Submitting…" : "Submit";
  }
}

function setDisabled(controls: HTMLButtonElement[], disabled: boolean): void {
  controls.forEach((control) => {
    control.disabled = disabled || control.dataset.enabled !== "true";
  });
}

function setResetEnabled(
  state: AttemptState,
  reset: HTMLButtonElement | undefined,
  enabled: boolean,
): void {
  if (!reset) return;
  reset.dataset.enabled = String(enabled);
  reset.disabled = !enabled || state.session.status !== "active";
}

function destroyControls(
  controls: HTMLButtonElement[],
  disposables: Disposable[],
  editor: EditorElements,
  confirmation: ConfirmationDialog,
  live: ReturnType<typeof createLiveRegion>,
): void {
  disposables.forEach((disposable) => disposable.dispose());
  controls.forEach((control) => control.replaceWith(control.cloneNode(true)));
  editor.conflict.remove();
  confirmation.dispose();
  live.dispose();
}
