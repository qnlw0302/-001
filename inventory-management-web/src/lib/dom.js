import { t } from "./i18n.js";

export const appRoot = document.querySelector("#app");

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function statusLabel(status) {
  if (status === "out") return t("status.out");
  if (status === "low") return t("status.low");
  return t("status.ok");
}

export function showMessage(element, text, type) {
  if (!element) return;
  element.textContent = text;
  element.className = `message ${type} show`;
}

export function clearMessage(element) {
  if (!element) return;
  element.textContent = "";
  element.className = "message";
}

export function togglePasswordVisibility(inputSelector, buttonSelector) {
  const input = document.querySelector(inputSelector);
  const button = document.querySelector(buttonSelector);
  if (!input || !button) return;
  if (input.type === "password") {
    input.type = "text";
    button.textContent = t("common.hide");
    button.setAttribute("aria-label", t("common.hidePassword"));
  } else {
    input.type = "password";
    button.textContent = t("common.show");
    button.setAttribute("aria-label", t("common.showPassword"));
  }
}
