import { request } from "../lib/api.js";
import { appRoot, clearMessage, escapeHtml, showMessage, togglePasswordVisibility } from "../lib/dom.js";
import { state } from "../lib/state.js";
import { toast } from "../lib/toast.js";
import { createFieldValidator, required } from "../lib/validation.js";
import { withButtonLoading } from "../lib/focus-trap.js";

export function renderLoginView({ renderRegisterView, renderInventoryView, loadProducts }) {
  const savedUsername = window.localStorage.getItem("inventoryUsername") || "";
  const savedRemember = window.localStorage.getItem("inventoryRemember") === "1";

  appRoot.innerHTML = `
    <main class="auth-page">
      <section class="auth-card">
        <header class="auth-heading">
          <h1>Inventory Management</h1>
          <p>Sign in to manage your inventory.</p>
        </header>

        <div id="loginMessage" class="message" role="alert" aria-live="assertive"></div>

        <form id="loginForm" class="stack" autocomplete="on" novalidate>
          <div class="field">
            <label for="loginUsername"><span>Username</span></label>
            <input id="loginUsername" name="username" type="text" autocomplete="username" maxlength="64" required value="${escapeHtml(savedUsername)}" aria-describedby="loginUsernameError">
            <p id="loginUsernameError" class="field-error" hidden></p>
          </div>

          <div class="field">
            <label for="loginPassword"><span>Password</span></label>
            <div class="password-row">
              <input id="loginPassword" name="password" type="password" autocomplete="current-password" maxlength="128" required aria-describedby="loginPasswordError">
              <button id="togglePasswordButton" class="button ghost" type="button" aria-label="Show password">Show</button>
            </div>
            <p id="loginPasswordError" class="field-error" hidden></p>
          </div>

          <div class="auth-options">
            <label class="checkbox">
              <input id="rememberCheckbox" type="checkbox" ${savedRemember ? "checked" : ""}>
              <span>Remember me</span>
            </label>
          </div>

          <div class="actions">
            <button id="loginButton" class="button primary" type="submit">Log In</button>
          </div>

          <p class="auth-switch">No account yet? <button id="goRegisterButton" class="link-button" type="button">Create one</button></p>
        </form>
      </section>
    </main>
  `;

  const validator = createFieldValidator();
  validator.attach({
    input: document.querySelector("#loginUsername"),
    error: document.querySelector("#loginUsernameError"),
    validate: required("Username")
  });
  validator.attach({
    input: document.querySelector("#loginPassword"),
    error: document.querySelector("#loginPasswordError"),
    validate: required("Password")
  });

  document.querySelector("#togglePasswordButton").addEventListener("click", () =>
    togglePasswordVisibility("#loginPassword", "#togglePasswordButton")
  );
  document.querySelector("#loginForm").addEventListener("submit", (event) =>
    handleLoginSubmit(event, validator, { renderInventoryView, loadProducts })
  );
  document.querySelector("#goRegisterButton").addEventListener("click", renderRegisterView);

  document.querySelector("#loginUsername").focus();
}

async function handleLoginSubmit(event, validator, { renderInventoryView, loadProducts }) {
  event.preventDefault();
  const loginMessage = document.querySelector("#loginMessage");
  const button = document.querySelector("#loginButton");
  clearMessage(loginMessage);

  if (!validator.validateAll()) return;

  const username = document.querySelector("#loginUsername").value.trim();
  const password = document.querySelector("#loginPassword").value;
  const remember = document.querySelector("#rememberCheckbox").checked;

  try {
    await withButtonLoading(button, async () => {
      const payload = await request("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password, remember })
      });
      state.user = payload.user;
      persistRememberedUsername(username, remember);
      renderInventoryView();
      await loadProducts(1);
      toast.success(`Welcome back, ${payload.user.username}.`);
    }, "Signing in…");
  } catch (error) {
    showMessage(loginMessage, error.message, "error");
  }
}

export function persistRememberedUsername(username, remember) {
  if (remember) {
    window.localStorage.setItem("inventoryUsername", username);
    window.localStorage.setItem("inventoryRemember", "1");
  } else {
    window.localStorage.removeItem("inventoryUsername");
    window.localStorage.removeItem("inventoryRemember");
  }
}
