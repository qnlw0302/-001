const STORAGE_KEY = "inventoryLanguage";

export const SUPPORTED_LANGUAGES = [
  { code: "en", labelKey: "language.english", htmlLang: "en" },
  { code: "zh", labelKey: "language.chinese", htmlLang: "zh-CN" }
];

const dictionaries = {
  en: {
    "api.csrfFailed": "Could not establish session.",
    "api.invalidResponse": "Server returned an invalid response.",
    "api.networkError": "Unable to reach the server.",
    "api.requestFailed": "Request failed.",
    "auth.accountCreated": "Account created. Welcome, {username}.",
    "auth.alreadyHaveAccount": "Already have an account?",
    "auth.createAccount": "Create Account",
    "auth.createOne": "Create one",
    "auth.creating": "Creating...",
    "auth.firstUserBody": "Set up the first account for this app. You will use it to sign in from now on.",
    "auth.firstUserTitle": "Welcome",
    "auth.login": "Log In",
    "auth.loginBody": "Sign in to manage your inventory.",
    "auth.logout": "Log Out",
    "auth.noAccount": "No account yet?",
    "auth.registerBody": "Pick a username and password to start managing your inventory.",
    "auth.rememberMe": "Remember me",
    "auth.sessionExpired": "Your session expired. Please log in again.",
    "auth.signIn": "Sign in",
    "auth.signingIn": "Signing in...",
    "auth.passwordHint": "min 6 chars; avoid common passwords",
    "auth.usernameHint": "3-64 chars, no spaces",
    "auth.welcomeBack": "Welcome back, {username}.",
    "common.appName": "Inventory Management",
    "common.cancel": "Cancel",
    "common.close": "Close",
    "common.confirmPassword": "Confirm Password",
    "common.currentPassword": "Current Password",
    "common.delete": "Delete",
    "common.hide": "Hide",
    "common.hidePassword": "Hide password",
    "common.loading": "Loading...",
    "common.newPassword": "New Password",
    "common.note": "Note",
    "common.optional": "optional",
    "common.password": "Password",
    "common.reason": "Reason",
    "common.saveChanges": "Save Changes",
    "common.saving": "Saving...",
    "common.deleting": "Deleting...",
    "common.show": "Show",
    "common.showPassword": "Show password",
    "common.username": "Username",
    "common.value": "Value",
    "history.after": "After",
    "history.body": "Recent movements for {name} (SKU {sku}). Current: {stock}.",
    "history.change": "Change",
    "history.empty": "No movements yet.",
    "history.loading": "Loading...",
    "history.stockHistory": "Stock History",
    "history.stockHistoryFor": "Stock History - {name}",
    "history.type": "Type",
    "history.when": "When",
    "inventory.actions": "Actions",
    "inventory.addCustomField": "+ Add Field",
    "inventory.addFirstProduct": "Add your first product using the form above.",
    "inventory.adjust": "Adjust",
    "inventory.confirmDeleteBody": "Re-enter your password to delete this product.",
    "inventory.confirmDeleteTitle": "Confirm Delete",
    "inventory.customFields": "Custom Fields",
    "inventory.customFieldsHint": "Add any extra data you care about (category, supplier, color, etc.).",
    "inventory.default": "default",
    "inventory.defaultRestockAlert": "Default restock alert: below {threshold}",
    "inventory.deleteProduct": "Delete Product",
    "inventory.detailStatus": "Status",
    "inventory.duplicateCustomFieldKey": "Duplicate custom field key: {key}",
    "inventory.editProfile": "Edit Profile",
    "inventory.emptyCustomFields": "No custom fields.",
    "inventory.export": "Export",
    "inventory.exporting": "Exporting...",
    "inventory.exportFailed": "Export failed.",
    "inventory.exportedCsv": "Exported products.csv.",
    "inventory.fieldName": "Field name",
    "inventory.formBody": "Create a product or edit an existing one.",
    "inventory.get": "Get",
    "inventory.getProduct": "Get Product",
    "inventory.getProductBody": "Load one product by ID, then update or delete it.",
    "inventory.history": "History",
    "inventory.id": "ID",
    "inventory.insertProduct": "Insert Product",
    "inventory.inserting": "Inserting...",
    "inventory.loadProductIdPlaceholder": "Enter product ID",
    "inventory.lowStock": "Low Stock",
    "inventory.lowStockAlert": "Low Stock Alert",
    "inventory.lowStockHint": "leave blank to use the default of {threshold}",
    "inventory.name": "Name",
    "inventory.noCustomFieldsYet": "No custom fields yet.",
    "inventory.noMatches": "Nothing matches \"{term}\". Try a different search.",
    "inventory.noProductSelected": "No product selected.",
    "inventory.noProductSelectedHint": "Enter an ID above or pick a row from the table to view its details.",
    "inventory.noProductsFound": "No products found.",
    "inventory.outOfStock": "Out of Stock",
    "inventory.pageLabel": "Page {page} of {totalPages}",
    "inventory.paginationNext": "Next",
    "inventory.paginationPrevious": "Previous",
    "inventory.productDeleted": "Product deleted.",
    "inventory.productId": "Product ID",
    "inventory.productInserted": "Product inserted.",
    "inventory.productLoaded": "Product loaded.",
    "inventory.productName": "Product Name",
    "inventory.productUpdated": "Product updated.",
    "inventory.products": "Products",
    "inventory.productsBody": "Paginated list of all products. Low stock means stock is below the product threshold.",
    "inventory.receive": "Receive",
    "inventory.remove": "Remove",
    "inventory.removeField": "Remove",
    "inventory.removeFieldAria": "Remove field",
    "inventory.reset": "Reset",
    "inventory.restockThreshold": "Restock Threshold",
    "inventory.saveChanges": "Save Changes",
    "inventory.search": "Search",
    "inventory.searchAria": "Search products by SKU or name",
    "inventory.searchPlaceholder": "Search by SKU or name",
    "inventory.signedInAs": "Signed in as",
    "inventory.signedOut": "Signed out.",
    "inventory.sku": "SKU",
    "inventory.stock": "Stock",
    "inventory.stockQuantity": "Stock Quantity",
    "inventory.thresholdCustom": "custom",
    "inventory.totalProducts": "Total Products",
    "inventory.update": "Update",
    "inventory.updateModeReady": "Update mode ready.",
    "inventory.updateProduct": "Update Product",
    "inventory.useMovementHint": "Use Receive, Remove, or Adjust on the product row to change stock.",
    "language.chinese": "Chinese",
    "language.english": "English",
    "language.label": "Language",
    "movement.addStock": "Add Stock",
    "movement.adjustBody": "Set the absolute stock level for {name} (SKU {sku}). Current quantity: {stock}.",
    "movement.adjustStock": "Adjust Stock",
    "movement.customerReturn": "Customer return (Return)",
    "movement.damagedLost": "Damaged or lost (Damaged)",
    "movement.enterQuantity": "Enter a quantity.",
    "movement.newAbsoluteQuantity": "New absolute stock quantity",
    "movement.notePlaceholder": "e.g. Truck arrival, recount, sale to customer X",
    "movement.quantity": "Quantity",
    "movement.quantityGreater": "Quantity must be {min} or greater.",
    "movement.quantityInteger": "Quantity must be an integer.",
    "movement.quantityReceived": "Quantity received",
    "movement.quantityRemoved": "Quantity removed",
    "movement.receiveBody": "Add stock to {name} (SKU {sku}). Current quantity: {stock}.",
    "movement.receiveStock": "Receive Stock",
    "movement.removeBody": "Remove stock from {name} (SKU {sku}). Current quantity: {stock}.",
    "movement.removeStock": "Remove Stock",
    "movement.saveMovement": "Save Movement",
    "movement.saveNewQuantity": "Save New Quantity",
    "movement.soldUsed": "Sold or used (Remove)",
    "movement.stockAdded": "Stock added",
    "movement.stockAdjusted": "Stock adjusted",
    "movement.stockArrival": "Stock arrival (Receive)",
    "movement.stockMovement": "Stock Movement",
    "movement.stockRemoved": "Stock removed",
    "movement.success": "{prefix}: {name} is now {quantity}.",
    "password.body": "Enter your current password and pick a new one (minimum 6 characters).",
    "password.changed": "Password changed.",
    "password.confirmNewPassword": "Confirm New Password",
    "password.fillAll": "Fill in all fields.",
    "password.mismatch": "New passwords do not match.",
    "password.title": "Change Password",
    "password.update": "Update Password",
    "profile.body": "Update your username. Confirm with your current password.",
    "profile.enterBoth": "Enter username and current password.",
    "profile.title": "Edit Profile",
    "profile.updated": "Profile updated.",
    "restock.healthy": "Stock level is healthy.",
    "restock.low": "Stock is below {threshold}. Restock soon.",
    "restock.out": "Out of stock. Restock immediately.",
    "status.low": "Restock Soon",
    "status.ok": "OK",
    "status.out": "Out of Stock",
    "toast.dismiss": "Dismiss notification",
    "toast.notifications": "Notifications",
    "validation.confirmPassword": "Confirm your password.",
    "validation.integer": "{label} must be an integer.",
    "validation.lowStockInteger": "Low stock threshold must be an integer.",
    "validation.lowStockMin": "Low stock threshold must be 1 or greater.",
    "validation.minLength": "{label} must be at least {min} characters.",
    "validation.noWhitespace": "{label} must not contain whitespace.",
    "validation.passwordMismatch": "Passwords do not match.",
    "validation.required": "{label} is required.",
    "validation.validProductId": "Enter a valid product ID.",
    "validation.valueMin": "{label} must be {min} or greater."
  },
  zh: {
    "api.csrfFailed": "无法建立会话，请刷新后重试。",
    "api.invalidResponse": "服务器返回了无效响应。",
    "api.networkError": "无法连接服务器。",
    "api.requestFailed": "请求失败。",
    "auth.accountCreated": "账户已创建。欢迎，{username}。",
    "auth.alreadyHaveAccount": "已有账户？",
    "auth.createAccount": "创建账户",
    "auth.createOne": "创建一个",
    "auth.creating": "正在创建...",
    "auth.firstUserBody": "请为此应用设置第一个账户。之后你将使用它登录。",
    "auth.firstUserTitle": "欢迎",
    "auth.login": "登录",
    "auth.loginBody": "登录后管理你的库存。",
    "auth.logout": "退出登录",
    "auth.noAccount": "还没有账户？",
    "auth.registerBody": "选择用户名和密码，开始管理库存。",
    "auth.rememberMe": "记住我",
    "auth.sessionExpired": "会话已过期，请重新登录。",
    "auth.signIn": "登录",
    "auth.signingIn": "正在登录...",
    "auth.passwordHint": "至少 6 个字符；请避免常见密码",
    "auth.usernameHint": "3-64 个字符，不能有空格",
    "auth.welcomeBack": "欢迎回来，{username}。",
    "common.appName": "库存管理",
    "common.cancel": "取消",
    "common.close": "关闭",
    "common.confirmPassword": "确认密码",
    "common.currentPassword": "当前密码",
    "common.delete": "删除",
    "common.hide": "隐藏",
    "common.hidePassword": "隐藏密码",
    "common.loading": "正在加载...",
    "common.newPassword": "新密码",
    "common.note": "备注",
    "common.optional": "可选",
    "common.password": "密码",
    "common.reason": "原因",
    "common.saveChanges": "保存更改",
    "common.saving": "正在保存...",
    "common.deleting": "正在删除...",
    "common.show": "显示",
    "common.showPassword": "显示密码",
    "common.username": "用户名",
    "common.value": "值",
    "history.after": "变更后",
    "history.body": "{name}（SKU {sku}）的近期库存流水。当前库存：{stock}。",
    "history.change": "变化",
    "history.empty": "暂无库存流水。",
    "history.loading": "正在加载...",
    "history.stockHistory": "库存历史",
    "history.stockHistoryFor": "库存历史 - {name}",
    "history.type": "类型",
    "history.when": "时间",
    "inventory.actions": "操作",
    "inventory.addCustomField": "+ 添加字段",
    "inventory.addFirstProduct": "请使用上方表单添加第一个商品。",
    "inventory.adjust": "调整",
    "inventory.confirmDeleteBody": "请重新输入密码以删除此商品。",
    "inventory.confirmDeleteTitle": "确认删除",
    "inventory.customFields": "自定义字段",
    "inventory.customFieldsHint": "添加你关心的额外信息（分类、供应商、颜色等）。",
    "inventory.default": "默认",
    "inventory.defaultRestockAlert": "默认补货提醒：低于 {threshold}",
    "inventory.deleteProduct": "删除商品",
    "inventory.detailStatus": "状态",
    "inventory.duplicateCustomFieldKey": "自定义字段键重复：{key}",
    "inventory.editProfile": "编辑资料",
    "inventory.emptyCustomFields": "无自定义字段。",
    "inventory.export": "导出",
    "inventory.exporting": "正在导出...",
    "inventory.exportFailed": "导出失败。",
    "inventory.exportedCsv": "已导出 products.csv。",
    "inventory.fieldName": "字段名",
    "inventory.formBody": "创建新商品，或编辑已有商品。",
    "inventory.get": "查看",
    "inventory.getProduct": "获取商品",
    "inventory.getProductBody": "按 ID 加载一个商品，然后更新或删除它。",
    "inventory.history": "历史",
    "inventory.id": "ID",
    "inventory.insertProduct": "新增商品",
    "inventory.inserting": "正在新增...",
    "inventory.loadProductIdPlaceholder": "输入商品 ID",
    "inventory.lowStock": "低库存",
    "inventory.lowStockAlert": "低库存提醒",
    "inventory.lowStockHint": "留空则使用默认值 {threshold}",
    "inventory.name": "名称",
    "inventory.noCustomFieldsYet": "暂无自定义字段。",
    "inventory.noMatches": "没有匹配“{term}”的结果。请尝试其他搜索词。",
    "inventory.noProductSelected": "尚未选择商品。",
    "inventory.noProductSelectedHint": "在上方输入 ID，或从表格中选择一行查看详情。",
    "inventory.noProductsFound": "未找到商品。",
    "inventory.outOfStock": "缺货",
    "inventory.pageLabel": "第 {page} 页，共 {totalPages} 页",
    "inventory.paginationNext": "下一页",
    "inventory.paginationPrevious": "上一页",
    "inventory.productDeleted": "商品已删除。",
    "inventory.productId": "商品 ID",
    "inventory.productInserted": "商品已新增。",
    "inventory.productLoaded": "商品已加载。",
    "inventory.productName": "商品名称",
    "inventory.productUpdated": "商品已更新。",
    "inventory.products": "商品",
    "inventory.productsBody": "所有商品的分页列表。低库存表示库存低于该商品的提醒阈值。",
    "inventory.receive": "入库",
    "inventory.remove": "出库",
    "inventory.removeField": "移除",
    "inventory.removeFieldAria": "移除字段",
    "inventory.reset": "重置",
    "inventory.restockThreshold": "补货阈值",
    "inventory.saveChanges": "保存更改",
    "inventory.search": "搜索",
    "inventory.searchAria": "按 SKU 或名称搜索商品",
    "inventory.searchPlaceholder": "按 SKU 或名称搜索",
    "inventory.signedInAs": "当前用户",
    "inventory.signedOut": "已退出登录。",
    "inventory.sku": "SKU",
    "inventory.stock": "库存",
    "inventory.stockQuantity": "库存数量",
    "inventory.thresholdCustom": "自定义",
    "inventory.totalProducts": "商品总数",
    "inventory.update": "更新",
    "inventory.updateModeReady": "已进入更新模式。",
    "inventory.updateProduct": "更新商品",
    "inventory.useMovementHint": "请使用商品行中的入库、出库或调整来修改库存。",
    "language.chinese": "中文",
    "language.english": "English",
    "language.label": "语言",
    "movement.addStock": "增加库存",
    "movement.adjustBody": "将 {name}（SKU {sku}）的库存设置为绝对数量。当前库存：{stock}。",
    "movement.adjustStock": "调整库存",
    "movement.customerReturn": "客户退货（退回）",
    "movement.damagedLost": "损坏或丢失（损耗）",
    "movement.enterQuantity": "请输入数量。",
    "movement.newAbsoluteQuantity": "新的绝对库存数量",
    "movement.notePlaceholder": "例如：到货、盘点、销售给客户 X",
    "movement.quantity": "数量",
    "movement.quantityGreater": "数量必须大于等于 {min}。",
    "movement.quantityInteger": "数量必须是整数。",
    "movement.quantityReceived": "入库数量",
    "movement.quantityRemoved": "出库数量",
    "movement.receiveBody": "为 {name}（SKU {sku}）增加库存。当前库存：{stock}。",
    "movement.receiveStock": "入库",
    "movement.removeBody": "从 {name}（SKU {sku}）移除库存。当前库存：{stock}。",
    "movement.removeStock": "出库",
    "movement.saveMovement": "保存库存变更",
    "movement.saveNewQuantity": "保存新数量",
    "movement.soldUsed": "已售出或已使用（出库）",
    "movement.stockAdded": "库存已增加",
    "movement.stockAdjusted": "库存已调整",
    "movement.stockArrival": "到货入库（入库）",
    "movement.stockMovement": "库存变更",
    "movement.stockRemoved": "库存已移除",
    "movement.success": "{prefix}：{name} 当前库存为 {quantity}。",
    "password.body": "输入当前密码，并设置一个新密码（至少 6 个字符）。",
    "password.changed": "密码已修改。",
    "password.confirmNewPassword": "确认新密码",
    "password.fillAll": "请填写所有字段。",
    "password.mismatch": "两次输入的新密码不一致。",
    "password.title": "修改密码",
    "password.update": "更新密码",
    "profile.body": "更新用户名。请用当前密码确认。",
    "profile.enterBoth": "请输入用户名和当前密码。",
    "profile.title": "编辑资料",
    "profile.updated": "资料已更新。",
    "restock.healthy": "库存水平正常。",
    "restock.low": "库存低于 {threshold}，请尽快补货。",
    "restock.out": "当前缺货，请立即补货。",
    "status.low": "需要补货",
    "status.ok": "正常",
    "status.out": "缺货",
    "toast.dismiss": "关闭通知",
    "toast.notifications": "通知",
    "validation.confirmPassword": "请确认密码。",
    "validation.integer": "{label}必须是整数。",
    "validation.lowStockInteger": "低库存阈值必须是整数。",
    "validation.lowStockMin": "低库存阈值必须大于等于 1。",
    "validation.minLength": "{label}至少需要 {min} 个字符。",
    "validation.noWhitespace": "{label}不能包含空格。",
    "validation.passwordMismatch": "两次输入的密码不一致。",
    "validation.required": "{label}为必填项。",
    "validation.validProductId": "请输入有效的商品 ID。",
    "validation.valueMin": "{label}必须大于等于 {min}。"
  }
};

const serverErrorZh = {
  "Authentication required.": "请先登录。",
  "CSRF token missing or invalid.": "安全令牌缺失或无效，请刷新后重试。",
  "Current password is incorrect.": "当前密码不正确。",
  "Database operation failed.": "数据库操作失败。",
  "Format must be 'json' or 'csv'.": "格式必须是 json 或 csv。",
  "Forbidden.": "没有权限执行此操作。",
  "Invalid username or password.": "用户名或密码无效。",
  "New password must differ from current password.": "新密码必须与当前密码不同。",
  "Not found.": "未找到。",
  "Password does not match.": "密码不匹配。",
  "Password is required to confirm deletion.": "删除前必须输入密码确认。",
  "Product not found.": "未找到商品。",
  "Request body must be a JSON object.": "请求体必须是 JSON 对象。",
  "Request body must be valid JSON.": "请求体必须是有效的 JSON。",
  "SKU already exists.": "SKU 已存在。",
  "Stock quantity cannot be negative.": "库存数量不能为负数。",
  "Too many requests. Please wait before trying again.": "请求过于频繁，请稍后再试。",
  "Unexpected server error.": "服务器发生意外错误。",
  "User not found.": "未找到用户。",
  "Username already taken.": "用户名已被占用。"
};

const serverLabelZh = {
  "Custom field key": "自定义字段键",
  "Custom field keys": "自定义字段键",
  "Custom field value": "自定义字段值",
  "Current password": "当前密码",
  "Low stock threshold": "低库存阈值",
  "Name": "名称",
  "New password": "新密码",
  "Note": "备注",
  "Password": "密码",
  "Product name": "商品名称",
  "Quantity": "数量",
  "SKU": "SKU",
  "Stock quantity": "库存数量",
  "Username": "用户名",
  "limit": "每页数量",
  "page": "页码",
  "stock_qty": "库存数量",
  "low_stock_threshold": "低库存阈值"
};

// Stock-movement type names for Chinese error messages (server emits the English type).
const movementTypeZh = {
  receive: "入库",
  remove: "出库",
  return: "退回",
  damaged: "损耗",
  adjust: "调整"
};

function hasWindowStorage() {
  return typeof window !== "undefined" && window.localStorage;
}

function normalizeLanguage(language) {
  return SUPPORTED_LANGUAGES.some((item) => item.code === language) ? language : "en";
}

export function getLanguage() {
  if (!hasWindowStorage()) return "en";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored) return normalizeLanguage(stored);
  const browserLanguage = window.navigator && window.navigator.language;
  return browserLanguage && browserLanguage.toLowerCase().startsWith("zh") ? "zh" : "en";
}

export function setLanguage(language) {
  const next = normalizeLanguage(language);
  if (hasWindowStorage()) {
    window.localStorage.setItem(STORAGE_KEY, next);
  }
  applyLanguage(next);
  return next;
}

function formatMessage(template, params) {
  return String(template).replace(/\{(\w+)\}/g, (_match, key) =>
    params[key] == null ? "" : String(params[key])
  );
}

export function t(key, params = {}) {
  const language = getLanguage();
  const dictionary = dictionaries[language] || dictionaries.en;
  const template = dictionary[key] || dictionaries.en[key] || key;
  return formatMessage(template, params);
}

export function applyLanguage(language = getLanguage()) {
  if (typeof document === "undefined") return;
  const meta = SUPPORTED_LANGUAGES.find((item) => item.code === normalizeLanguage(language));
  document.documentElement.lang = meta ? meta.htmlLang : "en";
  document.title = t("common.appName");
}

export function renderLanguageSelect(id) {
  const current = getLanguage();
  const options = SUPPORTED_LANGUAGES.map((language) => `
    <option value="${language.code}" ${language.code === current ? "selected" : ""}>${t(language.labelKey)}</option>
  `).join("");
  return `
    <label class="language-select" for="${id}">
      <span>${t("language.label")}</span>
      <select id="${id}" name="language">${options}</select>
    </label>
  `;
}

export function bindLanguageSelect(selector, onChange) {
  const select = document.querySelector(selector);
  if (!select) return;
  select.addEventListener("change", () => {
    const previous = getLanguage();
    const next = setLanguage(select.value);
    if (next !== previous && typeof onChange === "function") onChange(next);
  });
}

function translateServerLabel(label) {
  return serverLabelZh[label] || label;
}

export function translateError(message) {
  if (!message || getLanguage() !== "zh") return message;
  if (serverErrorZh[message]) return serverErrorZh[message];

  let match = message.match(/^(.+) is required\.$/);
  if (match) return `${translateServerLabel(match[1])}为必填项。`;

  match = message.match(/^(.+) must be an integer\.$/);
  if (match) return `${translateServerLabel(match[1])}必须是整数。`;

  match = message.match(/^(.+) must be (\d+) or greater\.$/);
  if (match) return `${translateServerLabel(match[1])}必须大于等于 ${match[2]}。`;

  match = message.match(/^(.+) must be greater than 0\.$/);
  if (match) return `${translateServerLabel(match[1])}必须大于 0。`;

  match = message.match(/^(.+) must be at least (\d+) characters\.$/);
  if (match) return `${translateServerLabel(match[1])}至少需要 ${match[2]} 个字符。`;

  match = message.match(/^(.+) must be (\d+) characters or fewer\.$/);
  if (match) return `${translateServerLabel(match[1])}不能超过 ${match[2]} 个字符。`;

  match = message.match(/^At most (\d+) custom fields are allowed\.$/);
  if (match) return `最多允许 ${match[1]} 个自定义字段。`;

  match = message.match(/^Duplicate custom field key: '?(.+?)'?\.$/);
  if (match) return `自定义字段键重复：${match[1]}。`;

  // Stock movement errors (Stage 5). UI users hit these the moment they try
  // to over-remove or send a negative adjust; without these branches they'd
  // see English error text inside a Chinese-localized app.
  match = message.match(/^Cannot (\w+) (\d+) units?: only (\d+) in stock\.$/);
  if (match) {
    const typeZh = movementTypeZh[match[1]] || match[1];
    return `无法${typeZh} ${match[2]} 件：当前仅剩 ${match[3]} 件库存。`;
  }

  if (message === "Quantity must be 0 or greater for an adjustment.") {
    return "调整数量必须大于等于 0。";
  }

  if (message === "Quantity must be 1 or greater.") {
    return "数量必须大于等于 1。";
  }

  match = message.match(/^Movement type must be one of: (.+)\.$/);
  if (match) return `库存变更类型必须是以下之一：${match[1]}。`;

  if (message === "Unsupported movement type") {
    return "不支持的库存变更类型。";
  }

  if (
    message.startsWith("Stock quantity cannot be edited directly.")
  ) {
    return "库存数量不能直接修改，请使用商品行的入库、出库或调整按钮。";
  }

  return message;
}
