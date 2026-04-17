const state = {
  user: null,
  products: [],
  selectedProduct: null,
  page: 1,
  limit: 10,
  totalPages: 1,
  pendingDelete: null,
  defaultThreshold: 5,
  customFieldRows: []
};

let nextCustomRowId = 0;

const appRoot = document.querySelector("#app");

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function statusLabel(status) {
  if (status === "out") return "Out of Stock";
  if (status === "low") return "Restock Soon";
  return "OK";
}

async function request(path, options = {}) {
  const headers = {
    Accept: "application/json",
    ...(options.headers || {})
  };
  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers,
      credentials: "include"
    });
  } catch (error) {
    throw new Error("Unable to reach the server.");
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw new Error("Server returned an invalid response.");
    }
  }

  if (!response.ok) {
    const err = new Error((data && data.error) || "Request failed.");
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

function renderLoginView() {
  const savedUsername = window.localStorage.getItem("inventoryUsername") || "";
  const savedRemember = window.localStorage.getItem("inventoryRemember") === "1";

  appRoot.innerHTML = `
    <main class="auth-page">
      <section class="auth-card">
        <header class="auth-heading">
          <h1>Inventory Management</h1>
          <p>Sign in to manage your inventory.</p>
        </header>

        <div id="loginMessage" class="message"></div>

        <form id="loginForm" class="stack" autocomplete="on">
          <label class="field">
            <span>Username</span>
            <input id="loginUsername" name="username" type="text" autocomplete="username" maxlength="64" required value="${escapeHtml(savedUsername)}">
          </label>

          <label class="field">
            <span>Password</span>
            <div class="password-row">
              <input id="loginPassword" name="password" type="password" autocomplete="current-password" maxlength="128" required>
              <button id="togglePasswordButton" class="button ghost" type="button" aria-label="Show password">Show</button>
            </div>
          </label>

          <div class="auth-options">
            <label class="checkbox">
              <input id="rememberCheckbox" type="checkbox" ${savedRemember ? "checked" : ""}>
              <span>Remember me</span>
            </label>
          </div>

          <div class="actions">
            <button id="loginButton" class="button primary" type="submit">Log In</button>
          </div>
        </form>
      </section>
    </main>
  `;

  document.querySelector("#togglePasswordButton").addEventListener("click", togglePasswordVisibility);
  document.querySelector("#loginForm").addEventListener("submit", handleLoginSubmit);
}

function togglePasswordVisibility() {
  const input = document.querySelector("#loginPassword");
  const button = document.querySelector("#togglePasswordButton");
  if (input.type === "password") {
    input.type = "text";
    button.textContent = "Hide";
    button.setAttribute("aria-label", "Hide password");
  } else {
    input.type = "password";
    button.textContent = "Show";
    button.setAttribute("aria-label", "Show password");
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const loginMessage = document.querySelector("#loginMessage");
  const username = document.querySelector("#loginUsername").value.trim();
  const password = document.querySelector("#loginPassword").value;
  const remember = document.querySelector("#rememberCheckbox").checked;

  if (!username || !password) {
    showMessage(loginMessage, "Enter username and password.", "error");
    return;
  }

  try {
    const payload = await request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password, remember })
    });
    state.user = payload.user;
    if (remember) {
      window.localStorage.setItem("inventoryUsername", username);
      window.localStorage.setItem("inventoryRemember", "1");
    } else {
      window.localStorage.removeItem("inventoryUsername");
      window.localStorage.removeItem("inventoryRemember");
    }
    renderInventoryView();
    await loadProducts(1);
  } catch (error) {
    showMessage(loginMessage, error.message, "error");
  }
}

function renderInventoryView() {
  appRoot.innerHTML = `
    <main class="page">
      <header class="hero">
        <div>
          <h1>Inventory Management</h1>
        </div>
        <div class="hero-meta">
          <span class="threshold" id="defaultThresholdBadge">Default restock alert: below ${state.defaultThreshold}</span>
          <span class="user-badge">Signed in as <strong>${escapeHtml(state.user.username)}</strong></span>
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
          <input id="searchInput" type="text" placeholder="Search by SKU or name">
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

          <div id="formMessage" class="message"></div>

          <form id="productForm" class="stack">
            <input id="productId" type="hidden">

            <label class="field">
              <span>SKU</span>
              <input id="skuInput" name="sku" maxlength="64" required>
            </label>

            <label class="field">
              <span>Product Name</span>
              <input id="nameInput" name="name" maxlength="200" required>
            </label>

            <label class="field">
              <span>Stock Quantity</span>
              <input id="stockInput" name="stock_qty" type="number" min="0" value="0" required>
            </label>

            <label class="field">
              <span>Low Stock Alert <em class="field-hint">(leave blank to use the default of ${state.defaultThreshold})</em></span>
              <input id="thresholdInput" name="low_stock_threshold" type="number" min="1" placeholder="Use default">
            </label>

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

          <div id="detailMessage" class="message"></div>

          <div class="get-row">
            <input id="productLookupId" type="number" min="1" placeholder="Enter product ID">
            <button id="getProductButton" class="button secondary" type="button">Get Product</button>
          </div>

          <div id="detailCard" class="detail-card empty-state">No product selected.</div>

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

    <div id="confirmOverlay" class="modal-overlay" hidden>
      <div class="modal-card" role="dialog" aria-labelledby="confirmTitle">
        <h2 id="confirmTitle">Confirm Delete</h2>
        <p id="confirmBody">Re-enter your password to delete this product.</p>
        <div id="confirmMessage" class="message"></div>
        <form id="confirmForm" class="stack">
          <label class="field">
            <span>Password</span>
            <div class="password-row">
              <input id="confirmPassword" type="password" autocomplete="current-password" required>
              <button id="toggleConfirmPasswordButton" class="button ghost" type="button" aria-label="Show password">Show</button>
            </div>
          </label>
          <div class="actions">
            <button id="confirmCancelButton" class="button ghost" type="button">Cancel</button>
            <button id="confirmDeleteButton" class="button danger" type="submit">Delete</button>
          </div>
        </form>
      </div>
    </div>
  `;

  bindInventoryHandlers();
}

function bindInventoryHandlers() {
  document.querySelector("#logoutButton").addEventListener("click", handleLogout);
  document.querySelector("#productForm").addEventListener("submit", handleProductSubmit);
  document.querySelector("#resetButton").addEventListener("click", resetForm);
  document.querySelector("#addCustomFieldButton").addEventListener("click", () => addCustomFieldRow());
  document.querySelector("#customFieldsRows").addEventListener("click", handleCustomFieldsClick);
  document.querySelector("#searchButton").addEventListener("click", () => loadProducts(1).catch(showTopError));
  document.querySelector("#refreshButton").addEventListener("click", () => {
    document.querySelector("#searchInput").value = "";
    loadProducts(1).catch(showTopError);
  });
  document.querySelector("#searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadProducts(1).catch(showTopError);
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
  document.querySelector("#toggleConfirmPasswordButton").addEventListener("click", toggleConfirmPasswordVisibility);
  document.querySelector("#confirmForm").addEventListener("submit", handleConfirmedDelete);
  document.querySelector("#confirmOverlay").addEventListener("click", (event) => {
    if (event.target.id === "confirmOverlay") closeDeleteModal();
  });

  setCustomFieldRows({});
}

function showMessage(element, text, type) {
  element.textContent = text;
  element.className = `message ${type} show`;
}

function clearMessage(element) {
  element.textContent = "";
  element.className = "message";
}

function showTopError(error) {
  const formMessage = document.querySelector("#formMessage");
  if (formMessage) showMessage(formMessage, error.message, "error");
}

async function handleLogout() {
  try {
    await request("/api/auth/logout", { method: "POST" });
  } catch (error) {
    // Proceed to login view regardless.
  }
  state.user = null;
  state.selectedProduct = null;
  renderLoginView();
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
}

function setCustomFieldRows(fields) {
  state.customFieldRows = Object.entries(fields || {}).map(([key, value]) => ({
    id: nextCustomRowId++,
    key,
    value: value == null ? "" : String(value)
  }));
  renderCustomFieldRows();
}

function addCustomFieldRow(key = "", value = "") {
  state.customFieldRows.push({ id: nextCustomRowId++, key, value });
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
      <input type="text" data-role="key" placeholder="Field name" maxlength="64" value="${escapeHtml(row.key)}">
      <input type="text" data-role="value" placeholder="Value" maxlength="500" value="${escapeHtml(row.value)}">
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
  detailCard.textContent = "No product selected.";
  clearMessage(document.querySelector("#detailMessage"));
}

function renderTable(products) {
  const tableWrap = document.querySelector("#tableWrap");
  if (!products.length) {
    tableWrap.innerHTML = `<div class="empty-table">No products found.</div>`;
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
    <table>
      <thead>
        <tr>
          <th>ID</th><th>SKU</th><th>Name</th><th>Stock</th><th>Status</th><th>Actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderPagination() {
  const paginationWrap = document.querySelector("#paginationWrap");
  paginationWrap.innerHTML = `
    <button class="button ghost" type="button" id="prevPageButton" ${state.page <= 1 ? "disabled" : ""}>Previous</button>
    <span class="pagination-label">Page ${state.page} of ${state.totalPages}</span>
    <button class="button ghost" type="button" id="nextPageButton" ${state.page >= state.totalPages ? "disabled" : ""}>Next</button>
  `;

  document.querySelector("#prevPageButton").addEventListener("click", () => {
    if (state.page > 1) loadProducts(state.page - 1).catch(showTopError);
  });
  document.querySelector("#nextPageButton").addEventListener("click", () => {
    if (state.page < state.totalPages) loadProducts(state.page + 1).catch(showTopError);
  });
}

async function loadProducts(page = 1) {
  const search = document.querySelector("#searchInput").value.trim();
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

  try {
    const isUpdate = Boolean(productId);
    const product = isUpdate
      ? await request(`/api/products/${productId}`, { method: "PUT", body: JSON.stringify(payload) })
      : await request("/api/products", { method: "POST", body: JSON.stringify(payload) });

    renderSelectedProduct(product);
    fillForm(product);
    await loadProducts(state.page);
    showMessage(formMessage, isUpdate ? "Product updated." : "Product inserted.", "success");
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
  try {
    clearMessage(detailMessage);
    const product = await fetchOneProduct(productId);
    fillForm(product);
    showMessage(detailMessage, "Product loaded.", "success");
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

function openDeleteModal(productId) {
  state.pendingDelete = productId;
  const overlay = document.querySelector("#confirmOverlay");
  overlay.hidden = false;
  document.querySelector("#confirmPassword").value = "";
  clearMessage(document.querySelector("#confirmMessage"));
  document.querySelector("#confirmPassword").focus();
}

function closeDeleteModal() {
  state.pendingDelete = null;
  document.querySelector("#confirmOverlay").hidden = true;
}

function toggleConfirmPasswordVisibility() {
  const input = document.querySelector("#confirmPassword");
  const button = document.querySelector("#toggleConfirmPasswordButton");
  if (input.type === "password") {
    input.type = "text";
    button.textContent = "Hide";
    button.setAttribute("aria-label", "Hide password");
  } else {
    input.type = "password";
    button.textContent = "Show";
    button.setAttribute("aria-label", "Show password");
  }
}

async function handleConfirmedDelete(event) {
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

  try {
    await request(`/api/products/${state.pendingDelete}`, {
      method: "DELETE",
      body: JSON.stringify({ password })
    });
    if (state.selectedProduct && state.selectedProduct.id === state.pendingDelete) {
      clearSelectedProduct();
    }
    closeDeleteModal();
    resetForm();
    await loadProducts(state.page);
    showMessage(document.querySelector("#formMessage"), "Product deleted.", "success");
  } catch (error) {
    if (error.status === 401) return goToLogin();
    showMessage(confirmMessage, error.message, "error");
  }
}

function goToLogin() {
  state.user = null;
  renderLoginView();
  const loginMessage = document.querySelector("#loginMessage");
  if (loginMessage) showMessage(loginMessage, "Your session expired. Please log in again.", "error");
}

async function bootstrap() {
  try {
    const payload = await request("/api/auth/me");
    state.user = payload.user;
    renderInventoryView();
    await loadProducts(1);
  } catch (error) {
    if (error.status === 401) {
      renderLoginView();
      return;
    }
    renderLoginView();
    const loginMessage = document.querySelector("#loginMessage");
    if (loginMessage) showMessage(loginMessage, error.message, "error");
  }
}

bootstrap();
