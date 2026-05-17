import { request } from "../lib/api.js";
import { appRoot, clearMessage, showMessage, togglePasswordVisibility } from "../lib/dom.js";
import { state } from "../lib/state.js";
import { toast } from "../lib/toast.js";
import {
  combine,
  createFieldValidator,
  minLength,
  noWhitespace,
  required
} from "../lib/validation.js";
import { withButtonLoading } from "../lib/focus-trap.js";
import { persistRememberedUsername } from "./login.js";

export function renderRegisterView({ renderLoginView, renderInventoryView, loadProducts }) {
  appRoot.innerHTML = `
    <main class="auth-page">
      <section class="auth-card">
        <header class="auth-heading">
          <h1>Create Account</h1>
          <p>Pick a username and password to start managing your inventory.</p>
        </header>

        <div id="registerMessage" class="message" role="alert" aria-live="assertive"></div>

        <form id="registerForm" class="stack" autocomplete="on" novalidate>
          <div class="field">
            <label for="registerUsername"><span>Username <em class="field-hint">(3-64 chars, no spaces)</em></span></label>
            <input id="registerUsername" name="username" type="text" autocomplete="username" maxlength="64" required aria-describedby="registerUsernameError">
            <p id="registerUsernameError" class="field-error" hidden></p>
          </div>

          <div class="field">
            <label for="registerPassword"><span>Password <em class="field-hint">(min 6 chars; avoid common passwords)</em></span></label>
            <div class="password-row">
              <input id="registerPassword" name="password" type="password" autocomplete="new-password" minlength="6" maxlength="128" required aria-describedby="registerPasswordError">
              <button id="toggleRegisterPasswordButton" class="button ghost" type="button" aria-label="Show password">Show</button>
            </div>
            <p id="registerPasswordError" class="field-error" hidden></p>
          </div>

          <div class="field">
            <label for="registerPasswordConfirm"><span>Confirm Password</span></label>
            <input id="registerPasswordConfirm" type="password" autocomplete="new-password" minlength="6" maxlength="128" required aria-describedby="registerConfirmError">
            <p id="registerConfirmError" class="field-error" hidden></p>
          </div>

          <div class="auth-options">
            <label class="checkbox">
              <input id="registerRemember" type="checkbox">
              <span>Remember me</span>
            </label>
          </div>

          <div class="actions">
            <button id="registerButton" class="button primary" type="submit">Create Account</button>
          </div>

          <p class="auth-switch">Already have an account? <button id="goLoginButton" class="link-button" type="button">Sign in</button></p>
        </form>
      </section>
    </main>
  `;

  const validator = createFieldValidator();
  validator.attach({
    input: document.querySelector("#registerUsername"),
    error: document.querySelector("#registerUsernameError"),
    validate: combine(required("Username"), minLength("Username", 3), noWhitespace("Username"))
  });
  validator.attach({
    input: document.querySelector("#registerPassword"),
    error: document.querySelector("#registerPasswordError"),
    validate: combine(required("Password"), minLength("Password", 6))
  });
  validator.attach({
    input: document.querySelector("#registerPasswordConfirm"),
    error: document.querySelector("#registerConfirmError"),
    validate: (value) => {
      const password = document.querySelector("#registerPassword").value;
      if (!value) return "Confirm your password.";
      if (value !== password) return "Passwords do not match.";
      return null;
    }
  });

  document.querySelector("#toggleRegisterPasswordButton").addEventListener("click", () =>
    togglePasswordVisibility("#registerPassword", "#toggleRegisterPasswordButton")
  );
  document.querySelector("#registerForm").addEventListener("submit", (event) =>
    handleRegisterSubmit(event, validator, { renderInventoryView, loadProducts })
  );
  document.querySelector("#goLoginButton").addEventListener("click", renderLoginView);

  document.querySelector("#registerUsername").focus();
}

async function handleRegisterSubmit(event, validator, { renderInventoryView, loadProducts }) {
  event.preventDefault();
  const registerMessage = document.querySelector("#registerMessage");
  const button = document.querySelector("#registerButton");
  clearMessage(registerMessage);

  if (!validator.validateAll()) return;

  const username = document.querySelector("#registerUsername").value.trim();
  const password = document.querySelector("#registerPassword").value;
  const remember = document.querySelector("#registerRemember").checked;

  try {
    await withButtonLoading(button, async () => {
      const payload = await request("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password, remember })
      });
      state.user = payload.user;
      persistRememberedUsername(username, remember);
      renderInventoryView();
      await loadProducts(1);
      toast.success(`Account created. Welcome, ${payload.user.username}.`);
    }, "Creating…");
  } catch (error) {
    showMessage(registerMessage, error.message, "error");
  }
}
