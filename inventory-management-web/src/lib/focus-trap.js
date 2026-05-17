const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])"
].join(",");

/**
 * Trap keyboard focus within a modal container. Returns a cleanup function.
 *
 *   const release = trapFocus(modalEl, { onEscape: closeModal });
 *   // ... later, when the modal closes:
 *   release();
 *
 * Also remembers the previously-focused element and restores it on cleanup.
 */
export function trapFocus(container, options = {}) {
  if (!container) return () => {};
  const onEscape = typeof options.onEscape === "function" ? options.onEscape : null;
  const previouslyFocused = document.activeElement;

  function focusable() {
    return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
      (el) => el.offsetParent !== null || el === document.activeElement
    );
  }

  function handleKeydown(event) {
    if (event.key === "Escape" && onEscape) {
      event.preventDefault();
      onEscape();
      return;
    }
    if (event.key !== "Tab") return;
    const items = focusable();
    if (!items.length) {
      event.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  document.addEventListener("keydown", handleKeydown);

  // Focus the first focusable element (or the container itself).
  const items = focusable();
  if (items.length) items[0].focus();
  else if (container.tabIndex >= 0) container.focus();

  return function release() {
    document.removeEventListener("keydown", handleKeydown);
    if (previouslyFocused && typeof previouslyFocused.focus === "function") {
      try {
        previouslyFocused.focus();
      } catch (_error) {
        /* ignore */
      }
    }
  };
}

/**
 * Decorate a submit button so that while `task` runs it shows a busy state
 * (disabled + "Saving…" or the provided label). Restores the original text on
 * completion (or failure).
 */
export async function withButtonLoading(button, task, busyLabel = "Saving…") {
  if (!button) return task();
  const original = button.textContent;
  button.disabled = true;
  button.classList.add("is-loading");
  button.setAttribute("aria-busy", "true");
  button.textContent = busyLabel;
  try {
    return await task();
  } finally {
    button.disabled = false;
    button.classList.remove("is-loading");
    button.removeAttribute("aria-busy");
    button.textContent = original;
  }
}
