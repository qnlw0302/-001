import { clearCsrfToken, request } from "./lib/api.js";
import { showMessage } from "./lib/dom.js";
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

function showRegister() {
  renderRegisterView({
    renderLoginView: showLogin,
    renderInventoryView,
    loadProducts
  });
}

function goToLogin() {
  clearCsrfToken();
  state.user = null;
  showLogin();
  const loginMessage = document.querySelector("#loginMessage");
  if (loginMessage) showMessage(loginMessage, "Your session expired. Please log in again.", "error");
}

setGoToLogin(goToLogin);

async function bootstrap() {
  try {
    const payload = await request("/api/auth/me");
    state.user = payload.user;
    renderInventoryView();
    await loadProducts(1);
  } catch (error) {
    if (error.status === 401) {
      showLogin();
      return;
    }
    showLogin();
    const loginMessage = document.querySelector("#loginMessage");
    if (loginMessage) showMessage(loginMessage, error.message, "error");
  }
}

bootstrap();
