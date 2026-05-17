import { escapeHtml } from "./dom.js";

const TOAST_TIMEOUT_MS = 4500;
let containerEl = null;
let toastId = 0;

function ensureContainer() {
  if (containerEl && document.body.contains(containerEl)) return containerEl;
  containerEl = document.createElement("div");
  containerEl.className = "toast-stack";
  containerEl.setAttribute("role", "region");
  containerEl.setAttribute("aria-label", "Notifications");
  containerEl.setAttribute("aria-live", "polite");
  containerEl.setAttribute("aria-atomic", "false");
  document.body.appendChild(containerEl);
  return containerEl;
}

function dismiss(toastEl) {
  if (!toastEl || !toastEl.parentElement) return;
  toastEl.classList.add("toast-leave");
  setTimeout(() => {
    if (toastEl.parentElement) toastEl.parentElement.removeChild(toastEl);
  }, 180);
}

export function showToast(message, type = "info", { timeout = TOAST_TIMEOUT_MS } = {}) {
  if (!message) return;
  const container = ensureContainer();
  const id = ++toastId;
  const safeType = ["success", "error", "warning", "info"].includes(type) ? type : "info";

  const toastEl = document.createElement("div");
  toastEl.className = `toast toast-${safeType}`;
  toastEl.setAttribute("role", safeType === "error" ? "alert" : "status");
  toastEl.dataset.toastId = String(id);
  toastEl.innerHTML = `
    <span class="toast-message">${escapeHtml(message)}</span>
    <button type="button" class="toast-close" aria-label="Dismiss notification">&times;</button>
  `;
  toastEl.querySelector(".toast-close").addEventListener("click", () => dismiss(toastEl));
  container.appendChild(toastEl);

  if (timeout > 0) {
    setTimeout(() => dismiss(toastEl), timeout);
  }
  return id;
}

export const toast = {
  success: (message, opts) => showToast(message, "success", opts || {}),
  error: (message, opts) => showToast(message, "error", opts || {}),
  warning: (message, opts) => showToast(message, "warning", opts || {}),
  info: (message, opts) => showToast(message, "info", opts || {})
};
