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
import { nextRowId, state } from "../lib/state.js";
import { toast } from "../lib/toast.js";
import { createFieldValidator, integerMin, required } from "../lib/validation.js";
import {
  closeDeleteModal,
  closePasswordModal,
  closeProfileModal,
  handleConfirmedDelete,
  handlePasswordSubmit,
  handleProfileSubmit,
  openDeleteModal,
  openPasswordModal,
  openProfileModal
} from "./modals.js";

let productFormValidator = null;

export function renderInventoryView() {
  appRoot.innerHTML = `
    <main class="page">
      <header class="hero">
        <div>
          <h1>Inventory Management</h1>
        </div>
        <div class="hero-meta">
          <span class="threshold" id="defaultThresholdBadge">Default restock alert: below ${state.defaultThreshold}</span>
          <span class="user-badge">Signed in as <strong id="currentUsernameLabel">${escapeHtml(state.user.username)}</strong></span>
          <button id="editProfileButton" class="button ghost" type="button">Edit Profile</button>
          <button id="changePasswordButton" class="button ghost" type="button">Change Password</button>
          <button id="exportButton" class="button ghost" type="button">Export</button>
          <button id="logoutButton" class="button ghost" type="button">Log Out</button>
        </div>
      </header>

      <section class="stats">
        <article class="stat-card">
          <span>Total Products</span>
          <strong id="totalCount">0</strong>
        </article>
        <article class="stat-card">
          <span>Low Stock</span>
          <strong id="lowCount">0</strong>
        </article>
        <article class="stat-card">
          <span>Out of Stock</span>
          <strong id="outCount">0</strong>
        </article>
      </section>

      <section class="toolbar">
        <div class="toolbar-main">
          <input id="searchInput" type="text" placeholder="Search by SKU or name" aria-label="Search products by SKU or name">
          <button id="searchButton" class="button secondary" type="button">Search</button>
          <button id="refreshButton" class="button ghost" type="button">Reset</button>
        </div>
      </section>

      <section class="content">
        <article class="panel">
          <div class="panel-heading">
            <h2 id="formHeading">Insert Product</h2>
            <p>Create a product or edit an existing one.</p>
          </div>

          <div id="formMessage" class="message" role="status" aria-live="polite"></div>

          <form id="productForm" class="stack" novalidate>
            <input id="productId" type="hidden">

            <div class="field">
              <label for="skuInput"><span>SKU</span></label>
              <input id="skuInput" name="sku" maxlength="64" required aria-describedby="skuError">
              <p id="skuError" class="field-error" hidden></p>
            </div>

            <div class="field">
              <label for="nameInput"><span>Product Name</span></label>
              <input id="nameInput" name="name" maxlength="200" required aria-describedby="nameError">
              <p id="nameError" class="field-error" hidden></p>
            </div>

            <div class="field">
              <label for="stockInput"><span>Stock Quantity</span></label>
              <input id="stockInput" name="stock_qty" type="number" min="0" value="0" required aria-describedby="stockError">
              <p id="stockError" class="field-error" hidden></p>
            </div>

            <div class="field">
              <label for="thresholdInput"><span>Low Stock Alert <em class="field-hint">(leave blank to use the default of ${state.defaultThreshold})</em></span></label>
              <input id="thresholdInput" name="low_stock_threshold" type="number" min="1" placeholder="Use default" aria-describedby="thresholdError">
              <p id="thresholdError" class="field-error" hidden></p>
            </div>

            <fieldset class="field custom-fields">
              <legend><span>Custom Fields</span></legend>
              <p class="field-hint">Add any extra data you care about (category, supplier, color, etc.).</p>
              <div id="customFieldsRows" class="custom-fields-rows"></div>
              <button id="addCustomFieldButton" class="button ghost" type="button">+ Add Field</button>
            </fieldset>

            <div class="actions">
              <button id="submitButton" class="button primary" type="submit">Insert Product</button>
              <button id="resetButton" class="button ghost" type="button">Reset</button>
            </div>
          </form>
        </article>

        <article class="panel">
          <div class="panel-heading">
            <h2>Get Product</h2>
            <p>Load one product by ID, then update or delete it.</p>
          </div>

          <div id="detailMessage" class="message" role="status" aria-live="polite"></div>

          <div class="get-row">
            <input id="productLookupId" type="number" min="1" placeholder="Enter product ID" aria-label="Product ID">
            <button id="getProductButton" class="button secondary" type="button">Get Product</button>
          </div>

          <div id="detailCard" class="detail-card empty-state">
            <p class="empty-title">No product selected.</p>
            <p class="empty-hint">Enter an ID above or pick a row from the table to view its details.</p>
          </div>

          <div class="actions">
            <button id="editSelectedButton" class="button secondary" type="button" disabled>Update Product</button>
            <button id="deleteSelectedButton" class="button danger" type="button" disabled>Delete Product</button>
          </div>
        </article>
      </section>

      <section class="panel panel-table">
        <div class="panel-heading">
          <h2>Products</h2>
          <p>Paginated list of all products. Low stock means stock is between 1 and 4.</p>
        </div>
        <div id="tableWrap"></div>
        <div id="paginationWrap" class="pagination"></div>
      </section>
    </main>

    <div id="confirmOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="confirmTitle" tabindex="-1">
        <h2 id="confirmTitle">Confirm Delete</h2>
        <p id="confirmBody">Re-enter your password to delete this product.</p>
        <div id="confirmMessage" class="message" role="alert" aria-live="assertive"></div>
        <form id="confirmForm" class="stack" novalidate>
          <div class="field">
            <label for="confirmPassword"><span>Password</span></label>
            <div class="password-row">
              <input id="confirmPassword" type="password" autocomplete="current-password" required>
              <button id="toggleConfirmPasswordButton" class="button ghost" type="button" aria-label="Show password">Show</button>
            </div>
          </div>
          <div class="actions">
            <button id="confirmCancelButton" class="button ghost" type="button">Cancel</button>
            <button id="confirmDeleteButton" class="button danger" type="submit">Delete</button>
          </div>
        </form>
      </div>
    </div>

    <div id="profileOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="profileTitle" tabindex="-1">
        <h2 id="profileTitle">Edit Profile</h2>
        <p>Update your username. Confirm with your current password.</p>
        <div id="profileMessage" class="message" role="alert" aria-live="assertive"></div>
        <form id="profileForm" class="stack" novalidate>
          <div class="field">
            <label for="profileUsername"><span>Username</span></label>
            <input id="profileUsername" type="text" maxlength="64" required>
          </div>
          <div class="field">
            <label for="profileCurrentPassword"><span>Current Password</span></label>
            <input id="profileCurrentPassword" type="password" autocomplete="current-password" maxlength="128" required>
          </div>
          <div class="actions">
            <button id="profileCancelButton" class="button ghost" type="button">Cancel</button>
            <button id="profileSaveButton" class="button primary" type="submit">Save Changes</button>
          </div>
        </form>
      </div>
    </div>

    <div id="passwordOverlay" class="modal-overlay" hidden aria-hidden="true">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="passwordTitle" tabindex="-1">
        <h2 id="passwordTitle">Change Password</h2>
        <p>Enter your current password and pick a new one (minimum 6 characters).</p>
        <div id="passwordMessage" class="message" role="alert" aria-live="assertive"></div>
        <form id="passwordForm" class="stack" novalidate>
          <div class="field">
            <label for="passwordCurrent"><span>Current Password</span></label>
            <input id="passwordCurrent" type="password" autocomplete="current-password" maxlength="128" required>
          </div>
          <div class="field">
            <label for="passwordNew"><span>New Password</span></label>
            <input id="passwordNew" type="password" autocomplete="new-password" minlength="6" maxlength="128" required>
          </div>
          <div class="field">
            <label for="passwordNewConfirm"><span>Confirm New Password</span></label>
            <input id="passwordNewConfirm" type="password" autocomplete="new-password" minlength="6" maxlength="128" required>
          </div>
          <div class="actions">
            <button id="passwordCancelButton" class="button ghost" type="button">Cancel</button>
            <button id="passwordSaveButton" class="button primary" type="submit">Update Password</button>
          </div>
        </form>
      </div>
    </div>
  `;

  bindInventoryHandlers();
}

function bindInventoryHandlers() {
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

  productFormValidator = createFieldValidator();
  productFormValidator.attach({
    input: document.querySelector("#skuInput"),
    error: document.querySelector("#skuError"),
    validate: required("SKU")
  });
  productFormValidator.attach({
    input: document.querySelector("#nameInput"),
    error: document.querySelector("#nameError"),
    validate: required("Product name")
  });
  productFormValidator.attach({
    input: document.querySelector("#stockInput"),
    error: document.querySelector("#stockError"),
    validate: integerMin("Stock quantity", 0)
  });
  productFormValidator.attach({
    input: document.querySelector("#thresholdInput"),
    error: document.querySelector("#thresholdError"),
    validate: (value) => {
      if (value === "" || value == null) return null;
      const n = Number(value);
      if (!Number.isInteger(n)) return "Low stock threshold must be an integer.";
      if (n < 1) return "Low stock threshold must be 1 or greater.";
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
  toast.info("Signed out.");
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
  document.querySelector("#stockInput").value = "0";
  document.querySelector("#thresholdInput").value = "";
  setCustomFieldRows({});
  document.querySelector("#formHeading").textContent = "Insert Product";
  document.querySelector("#submitButton").textContent = "Insert Product";
  clearMessage(document.querySelector("#formMessage"));
  if (productFormValidator) productFormValidator.reset();
}

function fillForm(product) {
  document.querySelector("#productId").value = product.id;
  document.querySelector("#skuInput").value = product.sku;
  document.querySelector("#nameInput").value = product.name;
  document.querySelector("#stockInput").value = product.stock_qty;
  document.querySelector("#thresholdInput").value =
    product.low_stock_threshold == null ? "" : String(product.low_stock_threshold);
  setCustomFieldRows(product.custom_fields || {});
  document.querySelector("#formHeading").textContent = "Update Product";
  document.querySelector("#submitButton").textContent = "Save Changes";
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
    rowsEl.innerHTML = `<p class="custom-fields-empty">No custom fields yet.</p>`;
    return;
  }
  rowsEl.innerHTML = state.customFieldRows.map((row) => `
    <div class="custom-field-row" data-row-id="${row.id}">
      <input type="text" data-role="key" placeholder="Field name" maxlength="64" value="${escapeHtml(row.key)}" aria-label="Custom field name">
      <input type="text" data-role="value" placeholder="Value" maxlength="500" value="${escapeHtml(row.value)}" aria-label="Custom field value">
      <button type="button" class="button ghost custom-field-remove" data-remove="${row.id}" aria-label="Remove field">Remove</button>
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
      throw new Error(`Duplicate custom field key: ${key}`);
    }
    seen.add(key);
    result[key] = row.value;
  }
  return result;
}

function buildRestockMessage(product) {
  if (product.status === "out") return "Out of stock. Restock immediately.";
  if (product.needs_restock) return `Stock is below ${product.restock_threshold}. Restock soon.`;
  return "Stock level is healthy.";
}

function renderCustomFieldsList(fields) {
  const entries = Object.entries(fields || {});
  if (!entries.length) {
    return `<p class="detail-note custom-fields-empty">No custom fields.</p>`;
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
    ? `${product.restock_threshold} <span class="threshold-note">(default)</span>`
    : `${product.restock_threshold} <span class="threshold-note custom">(custom)</span>`;

  const detailCard = document.querySelector("#detailCard");
  detailCard.className = "detail-card";
  detailCard.innerHTML = `
    <div class="detail-grid">
      <div><span class="detail-label">ID</span><strong>${product.id}</strong></div>
      <div><span class="detail-label">SKU</span><strong>${escapeHtml(product.sku)}</strong></div>
      <div><span class="detail-label">Name</span><strong>${escapeHtml(product.name)}</strong></div>
      <div><span class="detail-label">Stock</span><strong>${product.stock_qty}</strong></div>
      <div><span class="detail-label">Restock Threshold</span><strong>${thresholdNote}</strong></div>
      <div><span class="detail-label">Status</span><strong><span class="badge ${product.status}">${statusLabel(product.status)}</span></strong></div>
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
    <p class="empty-title">No product selected.</p>
    <p class="empty-hint">Enter an ID above or pick a row from the table to view its details.</p>
  `;
  clearMessage(document.querySelector("#detailMessage"));
}

function renderTable(products) {
  const tableWrap = document.querySelector("#tableWrap");
  if (!products.length) {
    const term = document.querySelector("#searchInput")?.value.trim();
    tableWrap.innerHTML = `
      <div class="empty-table">
        <p class="empty-title">No products found.</p>
        <p class="empty-hint">${
          term
            ? `Nothing matches “${escapeHtml(term)}”. Try a different search.`
            : "Add your first product using the form above."
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
        <button class="table-link" type="button" data-view="${product.id}">Get</button>
        <button class="table-link" type="button" data-edit="${product.id}">Update</button>
        <button class="table-link danger-link" type="button" data-delete="${product.id}">Delete</button>
      </td>
    </tr>
  `).join("");

  tableWrap.innerHTML = `
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>SKU</th><th>Name</th><th>Stock</th><th>Status</th><th>Actions</th>
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
    <button class="button ghost" type="button" id="prevPageButton" ${state.page <= 1 ? "disabled" : ""}>Previous</button>
    <span class="pagination-label" aria-live="polite">Page ${state.page} of ${state.totalPages}</span>
    <button class="button ghost" type="button" id="nextPageButton" ${state.page >= state.totalPages ? "disabled" : ""}>Next</button>
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
    if (badge) badge.textContent = `Default restock alert: below ${state.defaultThreshold}`;
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

  const payload = {
    sku: document.querySelector("#skuInput").value.trim(),
    name: document.querySelector("#nameInput").value.trim(),
    stock_qty: Number(document.querySelector("#stockInput").value),
    low_stock_threshold: thresholdRaw === "" ? null : Number(thresholdRaw),
    custom_fields: customFields
  };

  const submitButton = document.querySelector("#submitButton");
  const isUpdate = Boolean(productId);

  try {
    await withButtonLoading(submitButton, async () => {
      const product = isUpdate
        ? await request(`/api/products/${productId}`, { method: "PUT", body: JSON.stringify(payload) })
        : await request("/api/products", { method: "POST", body: JSON.stringify(payload) });

      renderSelectedProduct(product);
      fillForm(product);
      await loadProducts(state.page);
      toast.success(isUpdate ? "Product updated." : "Product inserted.");
    }, isUpdate ? "Saving…" : "Inserting…");
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(formMessage, error.message, "error");
  }
}

async function handleGetProductClick() {
  const detailMessage = document.querySelector("#detailMessage");
  const productId = Number(document.querySelector("#productLookupId").value);
  if (!productId) {
    showMessage(detailMessage, "Enter a valid product ID.", "error");
    return;
  }
  const button = document.querySelector("#getProductButton");
  try {
    clearMessage(detailMessage);
    await withButtonLoading(button, async () => {
      const product = await fetchOneProduct(productId);
      fillForm(product);
      showMessage(detailMessage, "Product loaded.", "success");
    }, "Loading…");
  } catch (error) {
    showMessage(detailMessage, error.message, "error");
  }
}

async function handleTableClick(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const detailMessage = document.querySelector("#detailMessage");

  try {
    if (target.dataset.view) {
      const product = await fetchOneProduct(Number(target.dataset.view));
      fillForm(product);
      showMessage(detailMessage, "Product loaded.", "success");
      return;
    }
    if (target.dataset.edit) {
      const product = await fetchOneProduct(Number(target.dataset.edit));
      fillForm(product);
      showMessage(detailMessage, "Update mode ready.", "success");
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
        throw new Error("Export failed.");
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
      toast.success("Exported products.csv.");
    }, "Exporting…");
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
