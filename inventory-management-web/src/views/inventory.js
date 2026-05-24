import { clearCsrfToken, request } from "../lib/api.js";
import {
  appRoot,
  clearMessage,
  escapeHtml,
  showMessage,
  statusLabel,
  togglePasswordVisibility
} from "../lib/dom.js";
import { withButtonLoading } from "../lib/focus-trap.js";
import { bindLanguageSelect, renderLanguageSelect, t } from "../lib/i18n.js";
import { nextRowId, state } from "../lib/state.js";
import { toast } from "../lib/toast.js";
import { createFieldValidator, integerMin, required } from "../lib/validation.js";
import {
  closeDeleteModal,
  closeHistoryModal,
  closeMovementModal,
  closePasswordModal,
  closeProfileModal,
  handleConfirmedDelete,
  handleMovementSubmit,
  handlePasswordSubmit,
  handleProfileSubmit,
  openDeleteModal,
  openHistoryModal,
  openMovementModal,
  openPasswordModal,
  openProfileModal
} from "./modals.js";

let productFormValidator = null;

export function renderInventoryView() {
  appRoot.innerHTML = `
    <main class="page">
      <header class="hero">
        <div>
          <h1>${t("common.appName")}</h1>
        </div>
        <div class="hero-meta">
          ${renderLanguageSelect("inventoryLanguageSelect")}
          <span class="threshold" id="defaultThresholdBadge">${t("inventory.defaultRestockAlert", { threshold: state.defaultThreshold })}</span>
          <span class="user-badge">${t("inventory.signedInAs")} <strong id="currentUsernameLabel">${escapeHtml(state.user.username)}</strong></span>
          <button id="editProfileButton" class="button ghost" type="button">${t("inventory.editProfile")}</button>
          <button id="changePasswordButton" class="button ghost" type="button">${t("password.title")}</button>
          <button id="exportButton" class="button ghost" type="button">${t("inventory.export")}</button>
          <button id="logoutButton" class="button ghost" type="button">${t("auth.logout")}</button>
        </div>
      </header>

      <section class="stats">
        <article class="stat-card">
          <span>${t("inventory.totalProducts")}</span>
          <strong id="totalCount">0</strong>
        </article>
        <article class="stat-card">
          <span>${t("inventory.lowStock")}</span>
          <strong id="lowCount">0</strong>
        </article>
        <article class="stat-card">
          <span>${t("inventory.outOfStock")}</span>
          <strong id="outCount">0</strong>
        </article>
      </section>

      <section class="toolbar">
        <div class="toolbar-main">
          <input id="searchInput" type="text" placeholder="${t("inventory.searchPlaceholder")}" aria-label="${t("inventory.searchAria")}">
          <button id="searchButton" class="button secondary" type="button">${t("inventory.search")}</button>
          <button id="refreshButton" class="button ghost" type="button">${t("inventory.reset")}</button>
        </div>
      </section>

      <section class="content">
        <article class="panel">
          <div class="panel-heading">
            <h2 id="formHeading">${t("inventory.insertProduct")}</h2>
            <p>${t("inventory.formBody")}</p>
          </div>

          <div id="formMessage" class="message" role="status" aria-live="polite"></div>

          <form id="productForm" class="stack" novalidate>
            <input id="productId" type="hidden">

            <div class="field">
              <label for="skuInput"><span>${t("inventory.sku")}</span></label>
              <input id="skuInput" name="sku" maxlength="64" required aria-describedby="skuError">
              <p id="skuError" class="field-error" hidden></p>
            </div>

            <div class="field">
              <label for="nameInput"><span>${t("inventory.productName")}</span></label>
              <input id="nameInput" name="name" maxlength="200" required aria-describedby="nameError">
              <p id="nameError" class="field-error" hidden></p>
            </div>

            <div class="field">
              <label for="stockInput"><span>${t("inventory.stockQuantity")}</span></label>
              <input id="stockInput" name="stock_qty" type="number" min="0" value="0" required aria-describedby="stockError">
              <p id="stockError" class="field-error" hidden></p>
            </div>

            <div class="field">
              <label for="thresholdInput"><span>${t("inventory.lowStockAlert")} <em class="field-hint">(${t("inventory.lowStockHint", { threshold: state.defaultThreshold })})</em></span></label>
              <input id="thresholdInput" name="low_stock_threshold" type="number" min="1" placeholder="${t("inventory.default")}" aria-describedby="thresholdError">
              <p id="thresholdError" class="field-error" hidden></p>
            </div>

            <fieldset class="field custom-fields">
              <legend><span>${t("inventory.customFields")}</span></legend>
              <p class="field-hint">${t("inventory.customFieldsHint")}</p>
              <div id="customFieldsRows" class="custom-fields-rows"></div>
              <button id="addCustomFieldButton" class="button ghost" type="button">${t("inventory.addCustomField")}</button>
            </fieldset>

            <div class="actions">
              <button id="submitButton" class="button primary" type="submit">${t("inventory.insertProduct")}</button>
              <button id="resetButton" class="button ghost" type="button">${t("inventory.reset")}</button>
            </div>
          </form>
        </article>

        <article class="panel">
          <div class="panel-heading">
            <h2>${t("inventory.getProduct")}</h2>
            <p>${t("inventory.getProductBody")}</p>
          </div>

          <div id="detailMessage" class="message" role="status" aria-live="polite"></div>

          <div class="get-row">
            <input id="productLookupId" type="number" min="1" placeholder="${t("inventory.loadProductIdPlaceholder")}" aria-label="${t("inventory.productId")}">
            <button id="getProductButton" class="button secondary" type="button">${t("inventory.getProduct")}</button>
          </div>

          <div id="detailCard" class="detail-card empty-state">
            <p class="empty-title">${t("inventory.noProductSelected")}</p>
            <p class="empty-hint">${t("inventory.noProductSelectedHint")}</p>
          </div>

          <div class="actions">
            <button id="editSelectedButton" class="button secondary" type="button" disabled>${t("inventory.updateProduct")}</button>
            <button id="deleteSelectedButton" class="button danger" type="button" disabled>${t("inventory.deleteProduct")}</button>
          </div>
        </article>
      </section>

      <section class="panel panel-table">
        <div class="panel-heading">
          <h2>${t("inventory.products")}</h2>
          <p>${t("inventory.productsBody")}</p>
        </div>
        <div id="tableWrap"></div>
        <div id="paginationWrap" class="pagination"></div>
      </section>
    </main>

    <div id="confirmOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="confirmTitle" tabindex="-1">
        <h2 id="confirmTitle">${t("inventory.confirmDeleteTitle")}</h2>
        <p id="confirmBody">${t("inventory.confirmDeleteBody")}</p>
        <div id="confirmMessage" class="message" role="alert" aria-live="assertive"></div>
        <form id="confirmForm" class="stack" novalidate>
          <div class="field">
            <label for="confirmPassword"><span>${t("common.password")}</span></label>
            <div class="password-row">
              <input id="confirmPassword" type="password" autocomplete="current-password" required>
              <button id="toggleConfirmPasswordButton" class="button ghost" type="button" aria-label="${t("common.showPassword")}">${t("common.show")}</button>
            </div>
          </div>
          <div class="actions">
            <button id="confirmCancelButton" class="button ghost" type="button">${t("common.cancel")}</button>
            <button id="confirmDeleteButton" class="button danger" type="submit">${t("common.delete")}</button>
          </div>
        </form>
      </div>
    </div>

    <div id="profileOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="profileTitle" tabindex="-1">
        <h2 id="profileTitle">${t("profile.title")}</h2>
        <p>${t("profile.body")}</p>
        <div id="profileMessage" class="message" role="alert" aria-live="assertive"></div>
        <form id="profileForm" class="stack" novalidate>
          <div class="field">
            <label for="profileUsername"><span>${t("common.username")}</span></label>
            <input id="profileUsername" type="text" maxlength="64" required>
          </div>
          <div class="field">
            <label for="profileCurrentPassword"><span>${t("common.currentPassword")}</span></label>
            <input id="profileCurrentPassword" type="password" autocomplete="current-password" maxlength="128" required>
          </div>
          <div class="actions">
            <button id="profileCancelButton" class="button ghost" type="button">${t("common.cancel")}</button>
            <button id="profileSaveButton" class="button primary" type="submit">${t("common.saveChanges")}</button>
          </div>
        </form>
      </div>
    </div>

    <div id="passwordOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="passwordTitle" tabindex="-1">
        <h2 id="passwordTitle">${t("password.title")}</h2>
        <p>${t("password.body")}</p>
        <div id="passwordMessage" class="message" role="alert" aria-live="assertive"></div>
        <form id="passwordForm" class="stack" novalidate>
          <div class="field">
            <label for="passwordCurrent"><span>${t("common.currentPassword")}</span></label>
            <input id="passwordCurrent" type="password" autocomplete="current-password" maxlength="128" required>
          </div>
          <div class="field">
            <label for="passwordNew"><span>${t("common.newPassword")}</span></label>
            <input id="passwordNew" type="password" autocomplete="new-password" minlength="6" maxlength="128" required>
          </div>
          <div class="field">
            <label for="passwordNewConfirm"><span>${t("password.confirmNewPassword")}</span></label>
            <input id="passwordNewConfirm" type="password" autocomplete="new-password" minlength="6" maxlength="128" required>
          </div>
          <div class="actions">
            <button id="passwordCancelButton" class="button ghost" type="button">${t("common.cancel")}</button>
            <button id="passwordSaveButton" class="button primary" type="submit">${t("password.update")}</button>
          </div>
        </form>
      </div>
    </div>

    <div id="movementOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="movementTitle" tabindex="-1">
        <h2 id="movementTitle">${t("movement.stockMovement")}</h2>
        <p id="movementBody">-</p>
        <div id="movementMessage" class="message" role="alert" aria-live="assertive"></div>
        <form id="movementForm" class="stack" novalidate>
          <div class="field" id="movementTypeField" hidden>
            <label for="movementTypeSelect"><span>${t("common.reason")}</span></label>
            <select id="movementTypeSelect"></select>
          </div>
          <div class="field">
            <label for="movementQuantity"><span id="movementQuantityLabel">${t("movement.quantity")}</span></label>
            <input id="movementQuantity" type="number" required>
            <p id="movementQuantityError" class="field-error" hidden></p>
          </div>
          <div class="field">
            <label for="movementNote"><span>${t("common.note")} <em class="field-hint">(${t("common.optional")})</em></span></label>
            <input id="movementNote" type="text" maxlength="500" placeholder="${t("movement.notePlaceholder")}">
          </div>
          <div class="actions">
            <button id="movementCancelButton" class="button ghost" type="button">${t("common.cancel")}</button>
            <button id="movementSubmitButton" class="button primary" type="submit">${t("movement.saveMovement")}</button>
          </div>
        </form>
      </div>
    </div>

    <div id="historyOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card modal-card-wide" role="dialog" aria-modal="true" aria-labelledby="historyTitle" tabindex="-1">
        <h2 id="historyTitle">${t("history.stockHistory")}</h2>
        <p id="historyBody">-</p>
        <div id="historyMessage" class="message" role="status" aria-live="polite"></div>
        <div id="historyList" class="history-list"><p class="custom-fields-empty">${t("history.loading")}</p></div>
        <div class="actions">
          <button id="historyCloseButton" class="button ghost" type="button">${t("common.close")}</button>
        </div>
      </div>
    </div>
  `;

  bindInventoryHandlers();
}

function bindInventoryHandlers() {
  bindLanguageSelect("#inventoryLanguageSelect", () => {
    renderInventoryView();
    loadProducts(state.page).catch((error) => toast.error(error.message));
  });
  document.querySelector("#logoutButton").addEventListener("click", handleLogout);
  document.querySelector("#editProfileButton").addEventListener("click", openProfileModal);
  document.querySelector("#changePasswordButton").addEventListener("click", openPasswordModal);
  document.querySelector("#exportButton").addEventListener("click", handleExportClick);

  document.querySelector("#productForm").addEventListener("submit", handleProductSubmit);
  document.querySelector("#resetButton").addEventListener("click", resetForm);
  document.querySelector("#addCustomFieldButton").addEventListener("click", () => addCustomFieldRow());
  document.querySelector("#customFieldsRows").addEventListener("click", handleCustomFieldsClick);
  document.querySelector("#searchButton").addEventListener("click", () =>
    loadProducts(1).catch((error) => toast.error(error.message))
  );
  document.querySelector("#refreshButton").addEventListener("click", () => {
    document.querySelector("#searchInput").value = "";
    loadProducts(1).catch((error) => toast.error(error.message));
  });
  document.querySelector("#searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadProducts(1).catch((error) => toast.error(error.message));
    }
  });
  document.querySelector("#getProductButton").addEventListener("click", handleGetProductClick);
  document.querySelector("#editSelectedButton").addEventListener("click", () => {
    if (state.selectedProduct) fillForm(state.selectedProduct);
  });
  document.querySelector("#deleteSelectedButton").addEventListener("click", () => {
    if (state.selectedProduct) openDeleteModal(state.selectedProduct.id);
  });
  document.querySelector("#tableWrap").addEventListener("click", handleTableClick);

  document.querySelector("#confirmCancelButton").addEventListener("click", closeDeleteModal);
  document.querySelector("#toggleConfirmPasswordButton").addEventListener("click", () =>
    togglePasswordVisibility("#confirmPassword", "#toggleConfirmPasswordButton")
  );
  document.querySelector("#confirmForm").addEventListener("submit", (event) =>
    handleConfirmedDelete(event, {
      reloadAfter: () => loadProducts(state.page),
      clearSelectedProduct,
      resetForm,
      goToLogin
    })
  );
  document.querySelector("#confirmOverlay").addEventListener("click", (event) => {
    if (event.target.id === "confirmOverlay") closeDeleteModal();
  });

  document.querySelector("#profileCancelButton").addEventListener("click", closeProfileModal);
  document.querySelector("#profileForm").addEventListener("submit", (event) =>
    handleProfileSubmit(event, { goToLogin })
  );
  document.querySelector("#profileOverlay").addEventListener("click", (event) => {
    if (event.target.id === "profileOverlay") closeProfileModal();
  });

  document.querySelector("#passwordCancelButton").addEventListener("click", closePasswordModal);
  document.querySelector("#passwordForm").addEventListener("submit", (event) =>
    handlePasswordSubmit(event, { goToLogin })
  );
  document.querySelector("#passwordOverlay").addEventListener("click", (event) => {
    if (event.target.id === "passwordOverlay") closePasswordModal();
  });

  document.querySelector("#movementCancelButton").addEventListener("click", closeMovementModal);
  document.querySelector("#movementForm").addEventListener("submit", (event) =>
    handleMovementSubmit(event, {
      reloadAfter: () => loadProducts(state.page),
      goToLogin
    })
  );
  document.querySelector("#movementOverlay").addEventListener("click", (event) => {
    if (event.target.id === "movementOverlay") closeMovementModal();
  });

  document.querySelector("#historyCloseButton").addEventListener("click", closeHistoryModal);
  document.querySelector("#historyOverlay").addEventListener("click", (event) => {
    if (event.target.id === "historyOverlay") closeHistoryModal();
  });

  productFormValidator = createFieldValidator();
  productFormValidator.attach({
    input: document.querySelector("#skuInput"),
    error: document.querySelector("#skuError"),
    validate: required(t("inventory.sku"))
  });
  productFormValidator.attach({
    input: document.querySelector("#nameInput"),
    error: document.querySelector("#nameError"),
    validate: required(t("inventory.productName"))
  });
  productFormValidator.attach({
    input: document.querySelector("#stockInput"),
    error: document.querySelector("#stockError"),
    validate: integerMin(t("inventory.stockQuantity"), 0)
  });
  productFormValidator.attach({
    input: document.querySelector("#thresholdInput"),
    error: document.querySelector("#thresholdError"),
    validate: (value) => {
      if (value === "" || value == null) return null;
      const n = Number(value);
      if (!Number.isInteger(n)) return t("validation.lowStockInteger");
      if (n < 1) return t("validation.lowStockMin");
      return null;
    }
  });

  setCustomFieldRows({});
}

export async function handleLogout() {
  try {
    await request("/api/auth/logout", { method: "POST" });
  } catch (_error) {
    // Proceed to login view regardless.
  }
  clearCsrfToken();
  state.user = null;
  state.selectedProduct = null;
  toast.info(t("inventory.signedOut"));
  goToLogin();
}

function updateStats(summary) {
  document.querySelector("#totalCount").textContent = String(summary.total_products || 0);
  document.querySelector("#lowCount").textContent = String(summary.low_stock_products || 0);
  document.querySelector("#outCount").textContent = String(summary.out_of_stock_products || 0);
}

function resetForm() {
  document.querySelector("#productId").value = "";
  document.querySelector("#skuInput").value = "";
  document.querySelector("#nameInput").value = "";
  const stockInput = document.querySelector("#stockInput");
  stockInput.value = "0";
  stockInput.disabled = false;
  stockInput.removeAttribute("aria-describedby");
  const stockError = document.querySelector("#stockError");
  if (stockError) {
    stockError.hidden = true;
    stockError.textContent = "";
    stockError.className = "field-error";
  }
  document.querySelector("#thresholdInput").value = "";
  setCustomFieldRows({});
  document.querySelector("#formHeading").textContent = t("inventory.insertProduct");
  document.querySelector("#submitButton").textContent = t("inventory.insertProduct");
  clearMessage(document.querySelector("#formMessage"));
  if (productFormValidator) productFormValidator.reset();
}

function fillForm(product) {
  document.querySelector("#productId").value = product.id;
  document.querySelector("#skuInput").value = product.sku;
  document.querySelector("#nameInput").value = product.name;
  const stockInput = document.querySelector("#stockInput");
  stockInput.value = product.stock_qty;
  // Stock can no longer be edited through the product form — it changes only via
  // Receive / Remove / Adjust on the row. Disable the input and surface a hint.
  stockInput.disabled = true;
  const stockHint = document.querySelector("#stockError");
  if (stockHint) {
    stockHint.hidden = false;
    stockHint.textContent = t("inventory.useMovementHint");
    stockHint.className = "field-error field-hint";
  }
  document.querySelector("#thresholdInput").value =
    product.low_stock_threshold == null ? "" : String(product.low_stock_threshold);
  setCustomFieldRows(product.custom_fields || {});
  document.querySelector("#formHeading").textContent = t("inventory.updateProduct");
  document.querySelector("#submitButton").textContent = t("inventory.saveChanges");
  clearMessage(document.querySelector("#formMessage"));
  if (productFormValidator) productFormValidator.reset();
}

function setCustomFieldRows(fields) {
  state.customFieldRows = Object.entries(fields || {}).map(([key, value]) => ({
    id: nextRowId(),
    key,
    value: value == null ? "" : String(value)
  }));
  renderCustomFieldRows();
}

function addCustomFieldRow(key = "", value = "") {
  state.customFieldRows.push({ id: nextRowId(), key, value });
  renderCustomFieldRows();
  const rowsEl = document.querySelector("#customFieldsRows");
  const lastKeyInput = rowsEl.querySelector(".custom-field-row:last-child input[data-role='key']");
  if (lastKeyInput) lastKeyInput.focus();
}

function syncCustomFieldRowsFromDom() {
  const rowsEl = document.querySelector("#customFieldsRows");
  if (!rowsEl) return;
  state.customFieldRows.forEach((row) => {
    const rowEl = rowsEl.querySelector(`[data-row-id="${row.id}"]`);
    if (!rowEl) return;
    row.key = rowEl.querySelector("input[data-role='key']").value;
    row.value = rowEl.querySelector("input[data-role='value']").value;
  });
}

function renderCustomFieldRows() {
  const rowsEl = document.querySelector("#customFieldsRows");
  if (!rowsEl) return;
  if (!state.customFieldRows.length) {
    rowsEl.innerHTML = `<p class="custom-fields-empty">${t("inventory.noCustomFieldsYet")}</p>`;
    return;
  }
  rowsEl.innerHTML = state.customFieldRows.map((row) => `
    <div class="custom-field-row" data-row-id="${row.id}">
      <input type="text" data-role="key" placeholder="${t("inventory.fieldName")}" maxlength="64" value="${escapeHtml(row.key)}" aria-label="${t("inventory.fieldName")}">
      <input type="text" data-role="value" placeholder="${t("common.value")}" maxlength="500" value="${escapeHtml(row.value)}" aria-label="${t("common.value")}">
      <button type="button" class="button ghost custom-field-remove" data-remove="${row.id}" aria-label="${t("inventory.removeFieldAria")}">${t("inventory.removeField")}</button>
    </div>
  `).join("");
}

function handleCustomFieldsClick(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const removeId = target.dataset.remove;
  if (removeId != null) {
    syncCustomFieldRowsFromDom();
    state.customFieldRows = state.customFieldRows.filter((row) => String(row.id) !== removeId);
    renderCustomFieldRows();
  }
}

function collectCustomFields() {
  syncCustomFieldRowsFromDom();
  const result = {};
  const seen = new Set();
  for (const row of state.customFieldRows) {
    const key = row.key.trim();
    if (!key) continue;
    if (seen.has(key)) {
      throw new Error(t("inventory.duplicateCustomFieldKey", { key }));
    }
    seen.add(key);
    result[key] = row.value;
  }
  return result;
}

function buildRestockMessage(product) {
  if (product.status === "out") return t("restock.out");
  if (product.needs_restock) return t("restock.low", { threshold: product.restock_threshold });
  return t("restock.healthy");
}

function renderCustomFieldsList(fields) {
  const entries = Object.entries(fields || {});
  if (!entries.length) {
    return `<p class="detail-note custom-fields-empty">${t("inventory.emptyCustomFields")}</p>`;
  }
  const rows = entries.map(([key, value]) => `
    <div class="custom-field-view">
      <span class="detail-label">${escapeHtml(key)}</span>
      <strong>${escapeHtml(value == null ? "—" : String(value))}</strong>
    </div>
  `).join("");
  return `<div class="custom-fields-view">${rows}</div>`;
}

function renderSelectedProduct(product) {
  state.selectedProduct = product;
  document.querySelector("#productLookupId").value = String(product.id);
  document.querySelector("#editSelectedButton").disabled = false;
  document.querySelector("#deleteSelectedButton").disabled = false;

  const thresholdNote = product.low_stock_threshold == null
    ? `${product.restock_threshold} <span class="threshold-note">(${t("inventory.default")})</span>`
    : `${product.restock_threshold} <span class="threshold-note custom">(${t("inventory.thresholdCustom")})</span>`;

  const detailCard = document.querySelector("#detailCard");
  detailCard.className = "detail-card";
  detailCard.innerHTML = `
    <div class="detail-grid">
      <div><span class="detail-label">${t("inventory.id")}</span><strong>${product.id}</strong></div>
      <div><span class="detail-label">${t("inventory.sku")}</span><strong>${escapeHtml(product.sku)}</strong></div>
      <div><span class="detail-label">${t("inventory.name")}</span><strong>${escapeHtml(product.name)}</strong></div>
      <div><span class="detail-label">${t("inventory.stock")}</span><strong>${product.stock_qty}</strong></div>
      <div><span class="detail-label">${t("inventory.restockThreshold")}</span><strong>${thresholdNote}</strong></div>
      <div><span class="detail-label">${t("inventory.detailStatus")}</span><strong><span class="badge ${product.status}">${statusLabel(product.status)}</span></strong></div>
    </div>
    <p class="detail-note">${buildRestockMessage(product)}</p>
    ${renderCustomFieldsList(product.custom_fields)}
  `;
}

function clearSelectedProduct() {
  state.selectedProduct = null;
  document.querySelector("#productLookupId").value = "";
  document.querySelector("#editSelectedButton").disabled = true;
  document.querySelector("#deleteSelectedButton").disabled = true;
  const detailCard = document.querySelector("#detailCard");
  detailCard.className = "detail-card empty-state";
  detailCard.innerHTML = `
    <p class="empty-title">${t("inventory.noProductSelected")}</p>
    <p class="empty-hint">${t("inventory.noProductSelectedHint")}</p>
  `;
  clearMessage(document.querySelector("#detailMessage"));
}

function renderTable(products) {
  const tableWrap = document.querySelector("#tableWrap");
  if (!products.length) {
    const term = document.querySelector("#searchInput")?.value.trim();
    tableWrap.innerHTML = `
      <div class="empty-table">
        <p class="empty-title">${t("inventory.noProductsFound")}</p>
        <p class="empty-hint">${
          term
            ? t("inventory.noMatches", { term: escapeHtml(term) })
            : t("inventory.addFirstProduct")
        }</p>
      </div>
    `;
    return;
  }

  const rows = products.map((product) => `
    <tr>
      <td>${product.id}</td>
      <td>${escapeHtml(product.sku)}</td>
      <td>${escapeHtml(product.name)}</td>
      <td>${product.stock_qty}</td>
      <td><span class="badge ${product.status}">${statusLabel(product.status)}</span></td>
      <td class="action-cell">
        <button class="table-link" type="button" data-view="${product.id}">${t("inventory.get")}</button>
        <button class="table-link" type="button" data-edit="${product.id}">${t("inventory.update")}</button>
        <button class="table-link" type="button" data-receive="${product.id}">${t("inventory.receive")}</button>
        <button class="table-link" type="button" data-remove="${product.id}">${t("inventory.remove")}</button>
        <button class="table-link" type="button" data-adjust="${product.id}">${t("inventory.adjust")}</button>
        <button class="table-link" type="button" data-history="${product.id}">${t("inventory.history")}</button>
        <button class="table-link danger-link" type="button" data-delete="${product.id}">${t("common.delete")}</button>
      </td>
    </tr>
  `).join("");

  tableWrap.innerHTML = `
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>${t("inventory.id")}</th><th>${t("inventory.sku")}</th><th>${t("inventory.name")}</th><th>${t("inventory.stock")}</th><th>${t("inventory.detailStatus")}</th><th>${t("inventory.actions")}</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderPagination() {
  const paginationWrap = document.querySelector("#paginationWrap");
  paginationWrap.innerHTML = `
    <button class="button ghost" type="button" id="prevPageButton" ${state.page <= 1 ? "disabled" : ""}>${t("inventory.paginationPrevious")}</button>
    <span class="pagination-label" aria-live="polite">${t("inventory.pageLabel", { page: state.page, totalPages: state.totalPages })}</span>
    <button class="button ghost" type="button" id="nextPageButton" ${state.page >= state.totalPages ? "disabled" : ""}>${t("inventory.paginationNext")}</button>
  `;

  document.querySelector("#prevPageButton").addEventListener("click", () => {
    if (state.page > 1) loadProducts(state.page - 1).catch((error) => toast.error(error.message));
  });
  document.querySelector("#nextPageButton").addEventListener("click", () => {
    if (state.page < state.totalPages) loadProducts(state.page + 1).catch((error) => toast.error(error.message));
  });
}

export async function loadProducts(page = 1) {
  const search = document.querySelector("#searchInput")?.value.trim() || "";
  const query = new URLSearchParams({ page: String(page), limit: String(state.limit) });
  if (search) query.set("search", search);

  const payload = await request(`/api/products?${query.toString()}`);
  state.products = payload.items;
  state.page = payload.pagination.page;
  state.totalPages = payload.pagination.pages;
  if (payload.summary && typeof payload.summary.restock_threshold === "number") {
    state.defaultThreshold = payload.summary.restock_threshold;
    const badge = document.querySelector("#defaultThresholdBadge");
    if (badge) badge.textContent = t("inventory.defaultRestockAlert", { threshold: state.defaultThreshold });
  }
  updateStats(payload.summary);
  renderTable(payload.items);
  renderPagination();

  if (state.selectedProduct) {
    const current = payload.items.find((product) => product.id === state.selectedProduct.id);
    if (current) renderSelectedProduct(current);
  }
}

async function fetchOneProduct(productId) {
  const product = await request(`/api/products/${productId}`);
  renderSelectedProduct(product);
  return product;
}

async function handleProductSubmit(event) {
  event.preventDefault();
  const formMessage = document.querySelector("#formMessage");
  clearMessage(formMessage);

  if (productFormValidator && !productFormValidator.validateAll()) return;

  const productId = document.querySelector("#productId").value;
  const thresholdRaw = document.querySelector("#thresholdInput").value.trim();

  let customFields;
  try {
    customFields = collectCustomFields();
  } catch (error) {
    showMessage(formMessage, error.message, "error");
    return;
  }

  const submitButton = document.querySelector("#submitButton");
  const isUpdate = Boolean(productId);

  const payload = {
    sku: document.querySelector("#skuInput").value.trim(),
    name: document.querySelector("#nameInput").value.trim(),
    low_stock_threshold: thresholdRaw === "" ? null : Number(thresholdRaw),
    custom_fields: customFields
  };
  // stock_qty is only valid at insert time; PUT now rejects it (stock moves through movements).
  if (!isUpdate) {
    payload.stock_qty = Number(document.querySelector("#stockInput").value);
  }

  try {
    await withButtonLoading(submitButton, async () => {
      const product = isUpdate
        ? await request(`/api/products/${productId}`, { method: "PUT", body: JSON.stringify(payload) })
        : await request("/api/products", { method: "POST", body: JSON.stringify(payload) });

      renderSelectedProduct(product);
      fillForm(product);
      await loadProducts(state.page);
      toast.success(isUpdate ? t("inventory.productUpdated") : t("inventory.productInserted"));
    }, isUpdate ? t("common.saving") : t("inventory.inserting"));
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(formMessage, error.message, "error");
  }
}

async function handleGetProductClick() {
  const detailMessage = document.querySelector("#detailMessage");
  const productId = Number(document.querySelector("#productLookupId").value);
  if (!productId) {
    showMessage(detailMessage, t("validation.validProductId"), "error");
    return;
  }
  const button = document.querySelector("#getProductButton");
  try {
    clearMessage(detailMessage);
    await withButtonLoading(button, async () => {
      const product = await fetchOneProduct(productId);
      fillForm(product);
      showMessage(detailMessage, t("inventory.productLoaded"), "success");
    }, t("common.loading"));
  } catch (error) {
    showMessage(detailMessage, error.message, "error");
  }
}

async function handleTableClick(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const detailMessage = document.querySelector("#detailMessage");

  const findProduct = (id) => state.products.find((p) => p.id === id);

  try {
    if (target.dataset.view) {
      const product = await fetchOneProduct(Number(target.dataset.view));
      fillForm(product);
      showMessage(detailMessage, t("inventory.productLoaded"), "success");
      return;
    }
    if (target.dataset.edit) {
      const product = await fetchOneProduct(Number(target.dataset.edit));
      fillForm(product);
      showMessage(detailMessage, t("inventory.updateModeReady"), "success");
      return;
    }
    if (target.dataset.receive) {
      const product = findProduct(Number(target.dataset.receive));
      if (product) openMovementModal(product, "receive");
      return;
    }
    if (target.dataset.remove) {
      const product = findProduct(Number(target.dataset.remove));
      if (product) openMovementModal(product, "remove");
      return;
    }
    if (target.dataset.adjust) {
      const product = findProduct(Number(target.dataset.adjust));
      if (product) openMovementModal(product, "adjust");
      return;
    }
    if (target.dataset.history) {
      const product = findProduct(Number(target.dataset.history));
      if (product) openHistoryModal(product);
      return;
    }
    if (target.dataset.delete) {
      openDeleteModal(Number(target.dataset.delete));
    }
  } catch (error) {
    showMessage(detailMessage, error.message, "error");
  }
}

async function handleExportClick() {
  const button = document.querySelector("#exportButton");
  try {
    await withButtonLoading(button, async () => {
      const response = await fetch("/api/products/export?format=csv", {
        credentials: "include"
      });
      if (!response.ok) {
        throw new Error(t("inventory.exportFailed"));
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "products.csv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success(t("inventory.exportedCsv"));
    }, t("inventory.exporting"));
  } catch (error) {
    toast.error(error.message);
  }
}

let goToLoginHandler = () => {};
export function setGoToLogin(handler) {
  goToLoginHandler = handler;
}
function goToLogin() {
  goToLoginHandler();
}
