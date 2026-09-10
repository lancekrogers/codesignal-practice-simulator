import { createDialogFocusTrap } from "./a11y";

export type ConfirmationDialog = {
  element: HTMLDialogElement;
  open(
    opener: HTMLElement,
    title: string,
    description: string,
    confirmLabel: string,
    onConfirm: () => void,
  ): void;
  dispose(): void;
};

export function createConfirmationDialog(root: HTMLElement): ConfirmationDialog {
  const element = document.createElement("dialog");
  element.className = "confirmation";
  element.setAttribute("aria-labelledby", "action-confirmation-title");
  element.setAttribute("aria-describedby", "action-confirmation-description");
  const title = document.createElement("h2");
  title.id = "action-confirmation-title";
  const description = document.createElement("p");
  description.id = "action-confirmation-description";
  const confirm = document.createElement("button");
  confirm.type = "button";
  confirm.className = "primary";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "secondary";
  cancel.textContent = "Cancel";
  element.append(title, description, confirm, cancel);
  root.append(element);
  let action = (): void => undefined;
  const focus = createDialogFocusTrap(element, { initialFocus: confirm });
  const onCancel = (): void => focus.close();
  const onConfirm = (): void => {
    focus.close();
    action();
  };
  cancel.addEventListener("click", onCancel);
  confirm.addEventListener("click", onConfirm);
  return {
    element,
    open(opener, nextTitle, nextDescription, label, nextAction) {
      title.textContent = nextTitle;
      description.textContent = nextDescription;
      confirm.textContent = label;
      action = nextAction;
      focus.open(opener);
    },
    dispose() {
      cancel.removeEventListener("click", onCancel);
      confirm.removeEventListener("click", onConfirm);
      focus.close();
      focus.dispose();
      element.remove();
    },
  };
}
