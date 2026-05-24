import { t, translateError } from "./i18n.js";

let csrfToken = null;
let csrfPromise = null;

const MUTATING_METHODS = new Set(["POST", "PUT", "DELETE", "PATCH"]);

export function clearCsrfToken() {
  csrfToken = null;
  csrfPromise = null;
}

async function fetchCsrfToken() {
  if (csrfToken) return csrfToken;
  if (csrfPromise) return csrfPromise;
  csrfPromise = fetch("/api/auth/csrf", { credentials: "include" })
    .then(async (response) => {
      if (!response.ok) throw new Error(t("api.csrfFailed"));
      const data = await response.json();
      csrfToken = data.csrf_token;
      return csrfToken;
    })
    .catch((error) => {
      csrfPromise = null;
      throw error;
    });
  return csrfPromise;
}

async function doRequest(path, options, retried = false) {
  const method = (options.method || "GET").toUpperCase();
  const headers = {
    Accept: "application/json",
    ...(options.headers || {})
  };
  if (options.body) headers["Content-Type"] = "application/json";
  if (MUTATING_METHODS.has(method)) {
    headers["X-CSRF-Token"] = await fetchCsrfToken();
  }

  let response;
  try {
    response = await fetch(path, {
      ...options,
      method,
      headers,
      credentials: "include"
    });
  } catch (error) {
    throw new Error(t("api.networkError"));
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw new Error(t("api.invalidResponse"));
    }
  }

  if (!response.ok) {
    // CSRF token mismatch (session rotated) — refresh once and retry.
    if (response.status === 403 && data && typeof data.error === "string" && data.error.toLowerCase().includes("csrf") && !retried) {
      clearCsrfToken();
      return doRequest(path, options, true);
    }
    const err = new Error(translateError((data && data.error) || t("api.requestFailed")));
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

export function request(path, options = {}) {
  return doRequest(path, options);
}
