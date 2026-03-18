const state = {
  products: [],
  selectedProduct: null,
  page: 1,
  limit: 10,
  totalPages: 1
};

document.querySelector("#app").innerHTML = `
  <main class="page">
    <header class="hero">
      <div>
        <h1>Inventory Management</h1>
      </div>
      <div class="threshold">Restock alert when stock is below 5</div>
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
      <div class="toolbar-auth">
        <input id="apiKeyInput" type="password" placeholder="API key for create, update, delete">
        <button id="saveApiKeyButton" class="button ghost" type="button">Save Key</button>
      </div>
      <p class="toolbar-note">Local default API key: <code>dev-inventory-key</code> unless you override <code>INVENTORY_API_KEY</code>.</p>
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
`;

const formHeading = document.querySelector("#formHeading");
const formMessage = document.querySelector("#formMessage");
const detailMessage = document.querySelector("#detailMessage");
const submitButton = document.querySelector("#submitButton");
const productForm = document.querySelector("#productForm");
const productIdInput = document.querySelector("#productId");
const skuInput = document.querySelector("#skuInput");
const nameInput = document.querySelector("#nameInput");
const stockInput = document.querySelector("#stockInput");
const searchInput = document.querySelector("#searchInput");
const apiKeyInput = document.querySelector("#apiKeyInput");
const productLookupId = document.querySelector("#productLookupId");
const detailCard = document.querySelector("#detailCard");
const tableWrap = document.querySelector("#tableWrap");
const paginationWrap = document.querySelector("#paginationWrap");
const editSelectedButton = document.querySelector("#editSelectedButton");
const deleteSelectedButton = document.querySelector("#deleteSelectedButton");

function showMessage(element, text, type) {
  element.textContent = text;
  element.className = `message ${type} show`;
}

function clearMessage(element) {
  element.textContent = "";
  element.className = "message";
}

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

function getStoredApiKey() {
  return window.localStorage.getItem("inventoryApiKey") || "";
}

function saveApiKey() {
  window.localStorage.setItem("inventoryApiKey", apiKeyInput.value.trim());
  showMessage(formMessage, "API key saved in this browser.", "success");
}

function buildHeaders(options) {
  const headers = {
    Accept: "application/json",
    ...(options.headers || {})
  };

  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const apiKey = apiKeyInput.value.trim();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  return headers;
}

async function request(path, options = {}) {
  try {
    const response = await fetch(path, {
      ...options,
      headers: buildHeaders(options)
    });

    const text = await response.text();
    const data = text ? JSON.parse(text) : null;

    if (!response.ok) {
      throw new Error((data && data.error) || "Request failed.");
    }
    return data;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error("Server returned an invalid response.");
    }
    if (error instanceof TypeError) {
      throw new Error("Unable to reach the server.");
    }
    throw error;
  }
}

function updateStats(summary) {
  document.querySelector("#totalCount").textContent = String(summary.total_products || 0);
  document.querySelector("#lowCount").textContent = String(summary.low_stock_products || 0);
  document.querySelector("#outCount").textContent = String(summary.out_of_stock_products || 0);
}

function resetForm() {
  productIdInput.value = "";
  skuInput.value = "";
  nameInput.value = "";
  stockInput.value = "0";
  formHeading.textContent = "Insert Product";
  submitButton.textContent = "Insert Product";
  clearMessage(formMessage);
}

function fillForm(product) {
  productIdInput.value = product.id;
  skuInput.value = product.sku;
  nameInput.value = product.name;
  stockInput.value = product.stock_qty;
  formHeading.textContent = "Update Product";
  submitButton.textContent = "Save Changes";
  clearMessage(formMessage);
}

function buildRestockMessage(product) {
  if (product.status === "out") {
    return "Out of stock. Restock immediately.";
  }
  if (product.needs_restock) {
    return "Stock is below 5. Restock soon.";
  }
  return "Stock level is healthy.";
}

function renderSelectedProduct(product) {
  state.selectedProduct = product;
  productLookupId.value = String(product.id);
  editSelectedButton.disabled = false;
  deleteSelectedButton.disabled = false;

  detailCard.className = "detail-card";
  detailCard.innerHTML = `
    <div class="detail-grid">
      <div>
        <span class="detail-label">ID</span>
        <strong>${product.id}</strong>
      </div>
      <div>
        <span class="detail-label">SKU</span>
        <strong>${escapeHtml(product.sku)}</strong>
      </div>
      <div>
        <span class="detail-label">Name</span>
        <strong>${escapeHtml(product.name)}</strong>
      </div>
      <div>
        <span class="detail-label">Stock</span>
        <strong>${product.stock_qty}</strong>
      </div>
      <div>
        <span class="detail-label">Restock Threshold</span>
        <strong>${product.restock_threshold}</strong>
      </div>
      <div>
        <span class="detail-label">Status</span>
        <strong><span class="badge ${product.status}">${statusLabel(product.status)}</span></strong>
      </div>
    </div>
    <p class="detail-note">${buildRestockMessage(product)}</p>
  `;
}

function clearSelectedProduct() {
  state.selectedProduct = null;
  productLookupId.value = "";
  editSelectedButton.disabled = true;
  deleteSelectedButton.disabled = true;
  detailCard.className = "detail-card empty-state";
  detailCard.textContent = "No product selected.";
  clearMessage(detailMessage);
}

function renderTable(products) {
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
          <th>ID</th>
          <th>SKU</th>
          <th>Name</th>
          <th>Stock</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderPagination() {
  paginationWrap.innerHTML = `
    <button class="button ghost" type="button" id="prevPageButton" ${state.page <= 1 ? "disabled" : ""}>Previous</button>
    <span class="pagination-label">Page ${state.page} of ${state.totalPages}</span>
    <button class="button ghost" type="button" id="nextPageButton" ${state.page >= state.totalPages ? "disabled" : ""}>Next</button>
  `;

  document.querySelector("#prevPageButton").addEventListener("click", () => {
    if (state.page > 1) {
      loadProducts(state.page - 1).catch((error) => showMessage(formMessage, error.message, "error"));
    }
  });

  document.querySelector("#nextPageButton").addEventListener("click", () => {
    if (state.page < state.totalPages) {
      loadProducts(state.page + 1).catch((error) => showMessage(formMessage, error.message, "error"));
    }
  });
}

async function loadProducts(page = 1) {
  const search = searchInput.value.trim();
  const query = new URLSearchParams({
    page: String(page),
    limit: String(state.limit)
  });
  if (search) {
    query.set("search", search);
  }

  const payload = await request(`/api/products?${query.toString()}`);
  state.products = payload.items;
  state.page = payload.pagination.page;
  state.totalPages = payload.pagination.pages;
  updateStats(payload.summary);
  renderTable(payload.items);
  renderPagination();

  if (state.selectedProduct) {
    const current = payload.items.find((product) => product.id === state.selectedProduct.id);
    if (current) {
      renderSelectedProduct(current);
    }
  }
}

async function fetchOneProduct(productId) {
  const product = await request(`/api/products/${productId}`);
  renderSelectedProduct(product);
  return product;
}

async function handleDelete(productId) {
  if (!apiKeyInput.value.trim()) {
    throw new Error("Enter an API key before deleting.");
  }

  const confirmed = window.confirm("Delete this product?");
  if (!confirmed) {
    return;
  }

  await request(`/api/products/${productId}`, { method: "DELETE" });
  if (state.selectedProduct && state.selectedProduct.id === productId) {
    clearSelectedProduct();
  }
  resetForm();
  await loadProducts(state.page);
  showMessage(formMessage, "Product deleted.", "success");
}

productForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage(formMessage);

  if (!apiKeyInput.value.trim()) {
    showMessage(formMessage, "Enter an API key before saving changes.", "error");
    return;
  }

  const payload = {
    sku: skuInput.value.trim(),
    name: nameInput.value.trim(),
    stock_qty: Number(stockInput.value)
  };

  try {
    const isUpdate = Boolean(productIdInput.value);
    const product = isUpdate
      ? await request(`/api/products/${productIdInput.value}`, {
          method: "PUT",
          body: JSON.stringify(payload)
        })
      : await request("/api/products", {
          method: "POST",
          body: JSON.stringify(payload)
        });

    renderSelectedProduct(product);
    fillForm(product);
    await loadProducts(state.page);
    showMessage(formMessage, isUpdate ? "Product updated." : "Product inserted.", "success");
  } catch (error) {
    showMessage(formMessage, error.message, "error");
  }
});

document.querySelector("#resetButton").addEventListener("click", () => {
  resetForm();
});

document.querySelector("#searchButton").addEventListener("click", async () => {
  try {
    await loadProducts(1);
  } catch (error) {
    showMessage(formMessage, error.message, "error");
  }
});

document.querySelector("#refreshButton").addEventListener("click", async () => {
  searchInput.value = "";
  try {
    await loadProducts(1);
  } catch (error) {
    showMessage(formMessage, error.message, "error");
  }
});

document.querySelector("#saveApiKeyButton").addEventListener("click", () => {
  saveApiKey();
});

searchInput.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  try {
    await loadProducts(1);
  } catch (error) {
    showMessage(formMessage, error.message, "error");
  }
});

document.querySelector("#getProductButton").addEventListener("click", async () => {
  const productId = Number(productLookupId.value);
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
});

editSelectedButton.addEventListener("click", () => {
  if (!state.selectedProduct) {
    return;
  }
  fillForm(state.selectedProduct);
});

deleteSelectedButton.addEventListener("click", async () => {
  if (!state.selectedProduct) {
    return;
  }
  try {
    await handleDelete(state.selectedProduct.id);
  } catch (error) {
    showMessage(detailMessage, error.message, "error");
  }
});

tableWrap.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const viewId = target.dataset.view;
  const editId = target.dataset.edit;
  const deleteId = target.dataset.delete;

  try {
    if (viewId) {
      const product = await fetchOneProduct(Number(viewId));
      fillForm(product);
      showMessage(detailMessage, "Product loaded.", "success");
      return;
    }

    if (editId) {
      const product = await fetchOneProduct(Number(editId));
      fillForm(product);
      showMessage(detailMessage, "Update mode ready.", "success");
      return;
    }

    if (deleteId) {
      await handleDelete(Number(deleteId));
    }
  } catch (error) {
    showMessage(detailMessage, error.message, "error");
  }
});

apiKeyInput.value = getStoredApiKey();

loadProducts().catch((error) => {
  showMessage(formMessage, error.message, "error");
});
