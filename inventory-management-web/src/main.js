const apiBase = window.location.port === "5173" ? "http://127.0.0.1:5000" : window.location.origin;

const state = {
  products: [],
  selectedProduct: null
};

document.querySelector("#app").innerHTML = `
  <main class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Inventory Management</p>
        <h1>Product CRUD Dashboard</h1>
        <p class="summary">
          Create a product schema workflow and manage insert, get, update, delete, and list-all
          operations from one page.
        </p>
      </div>
      <div class="threshold">Low stock threshold: 5</div>
    </header>

    <section class="stats" id="stats">
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
      <input id="searchInput" type="text" placeholder="Search by SKU or name">
      <button id="searchButton" class="button secondary" type="button">Search</button>
      <button id="refreshButton" class="button ghost" type="button">List All Products</button>
    </section>

    <section class="content">
      <article class="panel">
        <div class="panel-heading">
          <h2 id="formHeading">Insert Product</h2>
          <p>Use the schema fields below to create or update a product.</p>
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
          <p>Fetch one product by ID and inspect its schema values.</p>
        </div>

        <div id="detailMessage" class="message"></div>

        <div class="get-row">
          <input id="productLookupId" type="number" min="1" placeholder="Enter product ID">
          <button id="getProductButton" class="button secondary" type="button">Get Product</button>
        </div>

        <div id="detailCard" class="detail-card empty-state">
          No product selected.
        </div>

        <div class="actions">
          <button id="editSelectedButton" class="button secondary" type="button" disabled>Update Product</button>
          <button id="deleteSelectedButton" class="button danger" type="button" disabled>Delete Product</button>
        </div>
      </article>
    </section>

    <section class="panel panel-table">
      <div class="panel-heading">
        <h2>List All Products</h2>
        <p>View, update, or delete any product in the inventory.</p>
      </div>
      <div id="tableWrap"></div>
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
const productLookupId = document.querySelector("#productLookupId");
const detailCard = document.querySelector("#detailCard");
const editSelectedButton = document.querySelector("#editSelectedButton");
const deleteSelectedButton = document.querySelector("#deleteSelectedButton");
const tableWrap = document.querySelector("#tableWrap");
const searchInput = document.querySelector("#searchInput");

function showMessage(element, text, type) {
  element.textContent = text;
  element.className = `message ${type} show`;
}

function clearMessage(element) {
  element.textContent = "";
  element.className = "message";
}

function statusLabel(status) {
  if (status === "out") return "Out of Stock";
  if (status === "low") return "Low Stock";
  return "OK";
}

function apiUrl(path) {
  return `${apiBase}${path}`;
}

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(data?.error || "Request failed.");
  }

  return data;
}

function updateStats(products) {
  const lowCount = products.filter((product) => product.status === "low").length;
  const outCount = products.filter((product) => product.status === "out").length;

  document.querySelector("#totalCount").textContent = String(products.length);
  document.querySelector("#lowCount").textContent = String(lowCount);
  document.querySelector("#outCount").textContent = String(outCount);
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
        <span class="detail-label">Low Stock Threshold</span>
        <strong>${product.low_stock_threshold}</strong>
      </div>
      <div>
        <span class="detail-label">Status</span>
        <strong><span class="badge ${product.status}">${statusLabel(product.status)}</span></strong>
      </div>
    </div>
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

  const rows = products
    .map(
      (product) => `
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
      `
    )
    .join("");

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

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function loadProducts() {
  const search = searchInput.value.trim();
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  const products = await request(`/api/products${query}`);
  state.products = products;
  updateStats(products);
  renderTable(products);

  if (state.selectedProduct) {
    const freshProduct = products.find((product) => product.id === state.selectedProduct.id);
    if (freshProduct) {
      renderSelectedProduct(freshProduct);
    } else {
      clearSelectedProduct();
    }
  }
}

async function fetchOneProduct(productId) {
  const product = await request(`/api/products/${productId}`);
  renderSelectedProduct(product);
  return product;
}

async function handleDelete(productId) {
  const confirmed = window.confirm("Delete this product?");
  if (!confirmed) return;

  await request(`/api/products/${productId}`, { method: "DELETE" });
  if (state.selectedProduct?.id === productId) {
    clearSelectedProduct();
  }
  resetForm();
  await loadProducts();
  showMessage(formMessage, "Product deleted.", "success");
}

productForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage(formMessage);

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
    await loadProducts();
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
    await loadProducts();
  } catch (error) {
    showMessage(formMessage, error.message, "error");
  }
});

document.querySelector("#refreshButton").addEventListener("click", async () => {
  searchInput.value = "";
  try {
    await loadProducts();
  } catch (error) {
    showMessage(formMessage, error.message, "error");
  }
});

searchInput.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  try {
    await loadProducts();
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
  if (!state.selectedProduct) return;
  fillForm(state.selectedProduct);
});

deleteSelectedButton.addEventListener("click", async () => {
  if (!state.selectedProduct) return;

  try {
    await handleDelete(state.selectedProduct.id);
  } catch (error) {
    showMessage(detailMessage, error.message, "error");
  }
});

tableWrap.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;

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

loadProducts().catch((error) => {
  showMessage(formMessage, error.message, "error");
});
