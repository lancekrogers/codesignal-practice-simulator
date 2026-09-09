export type Disposable = {
  dispose(): void;
};

export type RovingOptions = {
  orientation?: "horizontal" | "vertical";
  activate?(index: number): void;
};

export function createRovingNavigation(
  items: HTMLElement[],
  options: RovingOptions = {},
): Disposable & { setActive(index: number, focus?: boolean): void } {
  let active = Math.max(0, items.findIndex((item) => item.tabIndex === 0));
  if (active < 0) active = 0;
  const orientation = options.orientation || "horizontal";

  const setActive = (index: number, focus = false): void => {
    active = normalizeIndex(index, items.length);
    items.forEach((item, itemIndex) => {
      item.tabIndex = itemIndex === active ? 0 : -1;
    });
    if (focus) items[active]?.focus();
  };

  const onKeyDown = (event: KeyboardEvent): void => {
    const current = items.indexOf(event.currentTarget as HTMLElement);
    if (current < 0) return;
    const next = nextIndex(event.key, current, items.length, orientation);
    if (next === null) return;
    event.preventDefault();
    setActive(next, true);
    options.activate?.(next);
  };

  const onFocus = (event: FocusEvent): void => {
    const index = items.indexOf(event.currentTarget as HTMLElement);
    if (index >= 0) setActive(index);
  };

  items.forEach((item) => {
    item.addEventListener("keydown", onKeyDown);
    item.addEventListener("focus", onFocus);
  });
  setActive(active);
  return {
    setActive,
    dispose(): void {
      items.forEach((item) => {
        item.removeEventListener("keydown", onKeyDown);
        item.removeEventListener("focus", onFocus);
      });
    },
  };
}

function nextIndex(
  key: string,
  current: number,
  length: number,
  orientation: "horizontal" | "vertical",
): number | null {
  const previous = orientation === "vertical" ? "ArrowUp" : "ArrowLeft";
  const next = orientation === "vertical" ? "ArrowDown" : "ArrowRight";
  if (key === previous) return (current - 1 + length) % length;
  if (key === next) return (current + 1) % length;
  if (key === "Home") return 0;
  if (key === "End") return length - 1;
  return null;
}

function normalizeIndex(index: number, length: number): number {
  return length === 0 ? 0 : Math.max(0, Math.min(index, length - 1));
}

export function createLiveRegion(root: HTMLElement): {
  element: HTMLElement;
  announce(message: string): void;
  dispose(): void;
} {
  const element = document.createElement("p");
  element.className = "sr-status";
  element.setAttribute("role", "status");
  element.setAttribute("aria-live", "polite");
  element.setAttribute("aria-atomic", "true");
  element.textContent = "";
  let lastMessage = "";
  let pendingFrame: number | null = null;
  let disposed = false;
  root.append(element);
  return {
    element,
    announce(message: string): void {
      if (disposed || message === lastMessage) return;
      lastMessage = message;
      if (pendingFrame !== null) {
        window.cancelAnimationFrame(pendingFrame);
      }
      element.textContent = "";
      pendingFrame = window.requestAnimationFrame(() => {
        pendingFrame = null;
        element.textContent = message;
      });
    },
    dispose(): void {
      if (disposed) return;
      disposed = true;
      if (pendingFrame !== null) {
        window.cancelAnimationFrame(pendingFrame);
        pendingFrame = null;
      }
      element.remove();
    },
  };
}

export function focusFirstAction(container: HTMLElement): void {
  const target = container.querySelector<HTMLElement>(
    'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled])',
  );
  target?.focus();
}

export type DialogFocusOptions = {
  initialFocus?: HTMLElement;
  allowEscape?: boolean;
  onClose?(): void;
};

export function createDialogFocusTrap(
  dialog: HTMLDialogElement,
  options: DialogFocusOptions = {},
): Disposable & { open(opener?: HTMLElement): void; close(): void } {
  let opener: HTMLElement | null = null;
  let opened = false;

  const focusable = (): HTMLElement[] => dialogFocusable(dialog);
  const onKeyDown = (event: KeyboardEvent): void =>
    handleDialogKeyDown(event, dialog, focusable, options);
  const onClose = (): void => {
    opened = false;
    options.onClose?.();
    restoreFocus(opener);
    opener = null;
  };

  dialog.addEventListener("keydown", onKeyDown, true);
  dialog.addEventListener("close", onClose);
  return {
    open(nextOpener?: HTMLElement): void {
      opener = nextOpener || (document.activeElement as HTMLElement);
      if (!dialog.open) dialog.showModal();
      opened = true;
      const target = options.initialFocus || focusable()[0];
      if (target?.isConnected && !target.hasAttribute("disabled")) target.focus();
    },
    close(): void {
      if (dialog.open) dialog.close();
    },
    dispose(): void {
      dialog.removeEventListener("keydown", onKeyDown, true);
      dialog.removeEventListener("close", onClose);
      opened = false;
      opener = null;
    },
  };
}

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function dialogFocusable(dialog: HTMLDialogElement): HTMLElement[] {
  return [...dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)]
    .filter((item) => !item.hidden);
}

function handleDialogKeyDown(
  event: KeyboardEvent,
  dialog: HTMLDialogElement,
  focusable: () => HTMLElement[],
  options: DialogFocusOptions,
): void {
  if (event.key === "Escape") {
    event.preventDefault();
    if (options.allowEscape !== false && dialog.open) dialog.close();
    return;
  }
  if (event.key !== "Tab") return;
  trapDialogTab(event, focusable());
}

function trapDialogTab(event: KeyboardEvent, items: HTMLElement[]): void {
  if (items.length === 0) return;
  const index = items.indexOf(document.activeElement as HTMLElement);
  const next = event.shiftKey
    ? (index <= 0 ? items.length - 1 : index - 1)
    : (index < 0 || index === items.length - 1 ? 0 : index + 1);
  event.preventDefault();
  items[next]?.focus();
}

function restoreFocus(opener: HTMLElement | null): void {
  if (opener?.isConnected && !opener.hasAttribute("disabled")) opener.focus();
}

