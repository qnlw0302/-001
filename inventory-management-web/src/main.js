import { clearCsrfToken, request } from "./lib/api.js";
import { showMessage } from "./lib/dom.js";
import { applyLanguage, t } from "./lib/i18n.js";
import { state } from "./lib/state.js";
import { renderLoginView } from "./views/login.js";
import { renderRegisterView } from "./views/register.js";
import {
  loadProducts,
  renderInventoryView,
  setGoToLogin
} from "./views/inventory.js";

function showLogin() {
  renderLoginView({
    renderRegisterView: showRegister,
    renderInventoryView,
    loadProducts
  });
}

function showRegister(options = {}) {
  renderRegisterView({
    renderLoginView: showLogin,
    renderInventoryView,
    loadProducts,
    firstUser: !!options.firstUser
  });
}

function goToLogin() {
  clearCsrfToken();
  state.user = null;
  showLogin();
  const loginMessage = document.querySelector("#loginMessage");
  if (loginMessage) showMessage(loginMessage, t("auth.sessionExpired"), "error");
}

setGoToLogin(goToLogin);

async function bootstrap() {
  try {
    const payload = await request("/api/auth/bootstrap");
    if (payload.user) {
      state.user = payload.user;
      renderInventoryView();
      await loadProducts(1);
      return;
    }
    if (payload.has_users === false) {
      showRegister({ firstUser: true });
      return;
    }
    showLogin();
  } catch (error) {
    showLogin();
    const loginMessage = document.querySelector("#loginMessage");
    if (loginMessage) showMessage(loginMessage, error.message, "error");
  }
}

applyLanguage();
bootstrap();
