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
import { bindLanguageSelect, renderLanguageSelect, t } from "../lib/i18n.js";

export function renderRegisterView({ renderLoginView, renderInventoryView, loadProducts, firstUser = false }) {
  const headingTitle = firstUser ? t("auth.firstUserTitle") : t("auth.createAccount");
  const headingBody = firstUser
    ? t("auth.firstUserBody")
    : t("auth.registerBody");
  const switchLine = firstUser
    ? ""
    : `<p class="auth-switch">${t("auth.alreadyHaveAccount")} <button id="goLoginButton" class="link-button" type="button">${t("auth.signIn")}</button></p>`;

  appRoot.innerHTML = `
    <main class="auth-page">
      <section class="auth-card">
        <div class="auth-language">
          ${renderLanguageSelect("registerLanguageSelect")}
        </div>

        <header class="auth-heading">
          <h1>${headingTitle}</h1>
          <p>${headingBody}</p>
        </header>

        <div id="registerMessage" class="message" role="alert" aria-live="assertive"></div>

        <form id="registerForm" class="stack" autocomplete="on" novalidate>
          <div class="field">
            <label for="registerUsername"><span>${t("common.username")} <em class="field-hint">(${t("auth.usernameHint")})</em></span></label>
            <input id="registerUsername" name="username" type="text" autocomplete="username" maxlength="64" required aria-describedby="registerUsernameError">
            <p id="registerUsernameError" class="field-error" hidden></p>
          </div>

          <div class="field">
            <label for="registerPassword"><span>${t("common.password")} <em class="field-hint">(${t("auth.passwordHint")})</em></span></label>
            <div class="password-row">
              <input id="registerPassword" name="password" type="password" autocomplete="new-password" minlength="6" maxlength="128" required aria-describedby="registerPasswordError">
              <button id="toggleRegisterPasswordButton" class="button ghost" type="button" aria-label="${t("common.showPassword")}">${t("common.show")}</button>
            </div>
            <p id="registerPasswordError" class="field-error" hidden></p>
          </div>

          <div class="field">
            <label for="registerPasswordConfirm"><span>${t("common.confirmPassword")}</span></label>
            <input id="registerPasswordConfirm" type="password" autocomplete="new-password" minlength="6" maxlength="128" required aria-describedby="registerConfirmError">
            <p id="registerConfirmError" class="field-error" hidden></p>
          </div>

          <div class="auth-options">
            <label class="checkbox">
              <input id="registerRemember" type="checkbox">
              <span>${t("auth.rememberMe")}</span>
            </label>
          </div>

          <div class="actions">
            <button id="registerButton" class="button primary" type="submit">${t("auth.createAccount")}</button>
          </div>

          ${switchLine}
        </form>
      </section>
    </main>
  `;

  const validator = createFieldValidator();
  validator.attach({
    input: document.querySelector("#registerUsername"),
    error: document.querySelector("#registerUsernameError"),
    validate: combine(required(t("common.username")), minLength(t("common.username"), 3), noWhitespace(t("common.username")))
  });
  validator.attach({
    input: document.querySelector("#registerPassword"),
    error: document.querySelector("#registerPasswordError"),
    validate: combine(required(t("common.password")), minLength(t("common.password"), 6))
  });
  validator.attach({
    input: document.querySelector("#registerPasswordConfirm"),
    error: document.querySelector("#registerConfirmError"),
    validate: (value) => {
      const password = document.querySelector("#registerPassword").value;
      if (!value) return t("validation.confirmPassword");
      if (value !== password) return t("validation.passwordMismatch");
      return null;
    }
  });

  bindLanguageSelect("#registerLanguageSelect", () =>
    renderRegisterView({ renderLoginView, renderInventoryView, loadProducts, firstUser })
  );
  document.querySelector("#toggleRegisterPasswordButton").addEventListener("click", () =>
    togglePasswordVisibility("#registerPassword", "#toggleRegisterPasswordButton")
  );
  document.querySelector("#registerForm").addEventListener("submit", (event) =>
    handleRegisterSubmit(event, validator, { renderInventoryView, loadProducts })
  );
  const goLoginButton = document.querySelector("#goLoginButton");
  if (goLoginButton) {
    goLoginButton.addEventListener("click", renderLoginView);
  }

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
      toast.success(t("auth.accountCreated", { username: payload.user.username }));
    }, t("auth.creating"));
  } catch (error) {
    showMessage(registerMessage, error.message, "error");
  }
}
