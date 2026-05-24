import { request } from "../lib/api.js";
import { clearMessage, escapeHtml, showMessage, togglePasswordVisibility } from "../lib/dom.js";
import { trapFocus, withButtonLoading } from "../lib/focus-trap.js";
import { t } from "../lib/i18n.js";
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
    showMessage(confirmMessage, t("validation.required", { label: t("common.password") }), "error");
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
      toast.success(t("inventory.productDeleted"));
    }, t("common.deleting"));
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
    showMessage(profileMessage, t("profile.enterBoth"), "error");
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
      toast.success(t("profile.updated"));
    }, t("common.saving"));
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
    showMessage(passwordMessage, t("password.fillAll"), "error");
    return;
  }
  if (next !== confirm) {
    showMessage(passwordMessage, t("password.mismatch"), "error");
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
      toast.success(t("password.changed"));
    }, t("common.saving"));
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(passwordMessage, error.message, "error");
  }
}

export function togglePasswordVisibilityBound(inputSelector, buttonSelector) {
  togglePasswordVisibility(inputSelector, buttonSelector);
}

/* ----- Stock movements ----- */

const MOVEMENT_PRESETS = {
  receive: {
    titleKey: "movement.receiveStock",
    submitKey: "movement.addStock",
    qtyLabelKey: "movement.quantityReceived",
    qtyMin: 1,
    typeOptions: [
      { value: "receive", labelKey: "movement.stockArrival" },
      { value: "return", labelKey: "movement.customerReturn" }
    ],
    bodyKey: "movement.receiveBody",
    successKey: "movement.stockAdded"
  },
  remove: {
    titleKey: "movement.removeStock",
    submitKey: "movement.removeStock",
    qtyLabelKey: "movement.quantityRemoved",
    qtyMin: 1,
    typeOptions: [
      { value: "remove", labelKey: "movement.soldUsed" },
      { value: "damaged", labelKey: "movement.damagedLost" }
    ],
    bodyKey: "movement.removeBody",
    successKey: "movement.stockRemoved"
  },
  adjust: {
    titleKey: "movement.adjustStock",
    submitKey: "movement.saveNewQuantity",
    qtyLabelKey: "movement.newAbsoluteQuantity",
    qtyMin: 0,
    typeOptions: null,
    fixedType: "adjust",
    bodyKey: "movement.adjustBody",
    successKey: "movement.stockAdjusted"
  }
};

function movementBody(preset, product) {
  return t(preset.bodyKey, {
    name: `<strong>${escapeHtml(product.name)}</strong>`,
    sku: escapeHtml(product.sku),
    stock: `<strong>${product.stock_qty}</strong>`
  });
}

export function openMovementModal(product, action) {
  const preset = MOVEMENT_PRESETS[action];
  if (!preset) return;

  state.pendingMovement = { productId: product.id, action, productName: product.name };

  document.querySelector("#movementTitle").textContent = t(preset.titleKey);
  document.querySelector("#movementBody").innerHTML = movementBody(preset, product);
  document.querySelector("#movementQuantityLabel").textContent = t(preset.qtyLabelKey);
  document.querySelector("#movementSubmitButton").textContent = t(preset.submitKey);

  const typeField = document.querySelector("#movementTypeField");
  const typeSelect = document.querySelector("#movementTypeSelect");
  if (preset.typeOptions) {
    typeField.hidden = false;
    typeSelect.innerHTML = preset.typeOptions
      .map((opt) => `<option value="${opt.value}">${escapeHtml(t(opt.labelKey))}</option>`)
      .join("");
    typeSelect.value = preset.typeOptions[0].value;
  } else {
    typeField.hidden = true;
    typeSelect.innerHTML = "";
  }

  const qtyInput = document.querySelector("#movementQuantity");
  qtyInput.min = String(preset.qtyMin);
  qtyInput.value = action === "adjust" ? String(product.stock_qty) : "";
  document.querySelector("#movementNote").value = "";

  const qtyError = document.querySelector("#movementQuantityError");
  if (qtyError) {
    qtyError.hidden = true;
    qtyError.textContent = "";
  }
  clearMessage(document.querySelector("#movementMessage"));
  openOverlay("movementOverlay", "#movementQuantity", { onEscape: closeMovementModal });
}

export function closeMovementModal() {
  state.pendingMovement = null;
  closeOverlay("movementOverlay");
}

export async function handleMovementSubmit(event, { reloadAfter, goToLogin }) {
  event.preventDefault();
  const movementMessage = document.querySelector("#movementMessage");
  clearMessage(movementMessage);

  const pending = state.pendingMovement;
  if (!pending) {
    closeMovementModal();
    return;
  }
  const preset = MOVEMENT_PRESETS[pending.action];
  if (!preset) {
    closeMovementModal();
    return;
  }

  const qtyRaw = document.querySelector("#movementQuantity").value.trim();
  if (qtyRaw === "") {
    showMessage(movementMessage, t("movement.enterQuantity"), "error");
    return;
  }
  const qty = Number(qtyRaw);
  if (!Number.isInteger(qty)) {
    showMessage(movementMessage, t("movement.quantityInteger"), "error");
    return;
  }
  if (qty < preset.qtyMin) {
    showMessage(
      movementMessage,
      t("movement.quantityGreater", { min: preset.qtyMin }),
      "error"
    );
    return;
  }

  const movementType = preset.fixedType
    ? preset.fixedType
    : document.querySelector("#movementTypeSelect").value;
  const note = document.querySelector("#movementNote").value.trim() || undefined;
  const payload = { type: movementType, quantity: qty };
  if (note) payload.note = note;

  const button = document.querySelector("#movementSubmitButton");
  try {
    await withButtonLoading(button, async () => {
      const result = await request(
        `/api/products/${pending.productId}/movements`,
        { method: "POST", body: JSON.stringify(payload) }
      );
      closeMovementModal();
      await reloadAfter();
      toast.success(
        t("movement.success", {
          prefix: t(preset.successKey),
          name: pending.productName,
          quantity: result.product.stock_qty
        })
      );
    }, t("common.saving"));
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(movementMessage, error.message, "error");
  }
}

/* ----- Stock movement history ----- */

const MOVEMENT_TYPE_LABEL = {
  receive: "inventory.receive",
  return: "movement.customerReturn",
  remove: "inventory.remove",
  damaged: "movement.damagedLost",
  adjust: "inventory.adjust"
};

export async function openHistoryModal(product) {
  document.querySelector("#historyTitle").textContent = t("history.stockHistoryFor", { name: product.name });
  document.querySelector("#historyBody").innerHTML =
    t("history.body", {
      name: `<strong>${escapeHtml(product.name)}</strong>`,
      sku: escapeHtml(product.sku),
      stock: `<strong>${product.stock_qty}</strong>`
    });
  const list = document.querySelector("#historyList");
  list.innerHTML = `<p class="custom-fields-empty">${t("history.loading")}</p>`;
  clearMessage(document.querySelector("#historyMessage"));
  openOverlay("historyOverlay", "#historyCloseButton", { onEscape: closeHistoryModal });

  try {
    const payload = await request(`/api/products/${product.id}/movements?limit=50`);
    const items = payload.items || [];
    if (!items.length) {
      list.innerHTML = `<p class="custom-fields-empty">${t("history.empty")}</p>`;
      return;
    }
    list.innerHTML = `
      <table class="history-table">
        <thead>
          <tr>
            <th>${t("history.when")}</th><th>${t("history.type")}</th><th>${t("history.change")}</th><th>${t("history.after")}</th><th>${t("common.note")}</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((m) => `
            <tr>
              <td>${escapeHtml(m.created_at)}</td>
              <td>${escapeHtml(MOVEMENT_TYPE_LABEL[m.movement_type] ? t(MOVEMENT_TYPE_LABEL[m.movement_type]) : m.movement_type)}</td>
              <td class="${m.quantity_delta < 0 ? "danger-link" : ""}">${m.quantity_delta > 0 ? "+" : ""}${m.quantity_delta}</td>
              <td>${m.quantity_after}</td>
              <td>${m.note ? escapeHtml(m.note) : "-"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (error) {
    list.innerHTML = "";
    showMessage(document.querySelector("#historyMessage"), error.message, "error");
  }
}

export function closeHistoryModal() {
  closeOverlay("historyOverlay");
}
