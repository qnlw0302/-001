import { request } from "../lib/api.js";
import { clearMessage, showMessage, togglePasswordVisibility } from "../lib/dom.js";
import { trapFocus, withButtonLoading } from "../lib/focus-trap.js";
import { state } from "../lib/state.js";
import { toast } from "../lib/toast.js";

const traps = new Map();

function openOverlay(overlayId, focusSelector, { onEscape } = {}) {
  const overlay = document.querySelector(`#${overlayId}`);
  if (!overlay) return;
  overlay.hidden = false;
  overlay.setAttribute("aria-hidden", "false");
  const focusTarget = focusSelector ? overlay.querySelector(focusSelector) : null;
  if (focusTarget) focusTarget.focus();
  const release = trapFocus(overlay, {
    onEscape: typeof onEscape === "function" ? onEscape : null
  });
  traps.set(overlayId, release);
}

function closeOverlay(overlayId) {
  const overlay = document.querySelector(`#${overlayId}`);
  if (!overlay) return;
  overlay.hidden = true;
  overlay.setAttribute("aria-hidden", "true");
  const release = traps.get(overlayId);
  if (release) release();
  traps.delete(overlayId);
}

/* ----- Delete confirmation ----- */

export function openDeleteModal(productId) {
  state.pendingDelete = productId;
  document.querySelector("#confirmPassword").value = "";
  clearMessage(document.querySelector("#confirmMessage"));
  openOverlay("confirmOverlay", "#confirmPassword", { onEscape: closeDeleteModal });
}

export function closeDeleteModal() {
  state.pendingDelete = null;
  closeOverlay("confirmOverlay");
}

export async function handleConfirmedDelete(event, { reloadAfter, clearSelectedProduct, resetForm, goToLogin }) {
  event.preventDefault();
  const confirmMessage = document.querySelector("#confirmMessage");
  const password = document.querySelector("#confirmPassword").value;
  if (!password) {
    showMessage(confirmMessage, "Enter your password.", "error");
    return;
  }
  if (state.pendingDelete == null) {
    closeDeleteModal();
    return;
  }

  const button = document.querySelector("#confirmDeleteButton");
  try {
    await withButtonLoading(button, async () => {
      await request(`/api/products/${state.pendingDelete}`, {
        method: "DELETE",
        body: JSON.stringify({ password })
      });
      if (state.selectedProduct && state.selectedProduct.id === state.pendingDelete) {
        clearSelectedProduct();
      }
      closeDeleteModal();
      resetForm();
      await reloadAfter();
      toast.success("Product deleted.");
    }, "Deleting…");
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(confirmMessage, error.message, "error");
  }
}

/* ----- Profile (username) ----- */

export function openProfileModal() {
  document.querySelector("#profileUsername").value = state.user ? state.user.username : "";
  document.querySelector("#profileCurrentPassword").value = "";
  clearMessage(document.querySelector("#profileMessage"));
  openOverlay("profileOverlay", "#profileUsername", { onEscape: closeProfileModal });
}

export function closeProfileModal() {
  closeOverlay("profileOverlay");
}

export async function handleProfileSubmit(event, { goToLogin }) {
  event.preventDefault();
  const profileMessage = document.querySelector("#profileMessage");
  const username = document.querySelector("#profileUsername").value.trim();
  const currentPassword = document.querySelector("#profileCurrentPassword").value;

  if (!username || !currentPassword) {
    showMessage(profileMessage, "Enter username and current password.", "error");
    return;
  }

  const button = document.querySelector("#profileSaveButton");
  try {
    await withButtonLoading(button, async () => {
      const payload = await request("/api/auth/me", {
        method: "PUT",
        body: JSON.stringify({ username, current_password: currentPassword })
      });
      state.user = payload.user;
      document.querySelector("#currentUsernameLabel").textContent = state.user.username;
      if (window.localStorage.getItem("inventoryRemember") === "1") {
        window.localStorage.setItem("inventoryUsername", state.user.username);
      }
      closeProfileModal();
      toast.success("Profile updated.");
    }, "Saving…");
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(profileMessage, error.message, "error");
  }
}

/* ----- Change password ----- */

export function openPasswordModal() {
  document.querySelector("#passwordCurrent").value = "";
  document.querySelector("#passwordNew").value = "";
  document.querySelector("#passwordNewConfirm").value = "";
  clearMessage(document.querySelector("#passwordMessage"));
  openOverlay("passwordOverlay", "#passwordCurrent", { onEscape: closePasswordModal });
}

export function closePasswordModal() {
  closeOverlay("passwordOverlay");
}

export async function handlePasswordSubmit(event, { goToLogin }) {
  event.preventDefault();
  const passwordMessage = document.querySelector("#passwordMessage");
  const current = document.querySelector("#passwordCurrent").value;
  const next = document.querySelector("#passwordNew").value;
  const confirm = document.querySelector("#passwordNewConfirm").value;

  if (!current || !next) {
    showMessage(passwordMessage, "Fill in all fields.", "error");
    return;
  }
  if (next !== confirm) {
    showMessage(passwordMessage, "New passwords do not match.", "error");
    return;
  }

  const button = document.querySelector("#passwordSaveButton");
  try {
    await withButtonLoading(button, async () => {
      await request("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next })
      });
      closePasswordModal();
      toast.success("Password changed.");
    }, "Saving…");
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(passwordMessage, error.message, "error");
  }
}

export function togglePasswordVisibilityBound(inputSelector, buttonSelector) {
  togglePasswordVisibility(inputSelector, buttonSelector);
}
