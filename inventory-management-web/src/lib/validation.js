/**
 * Tiny inline-validation helper.
 *
 * Attach validators per field via `attach({input, error, validate})`. The
 * helper wires up `blur` + `input` listeners that show/clear an error
 * message next to the field. Call `validateAll()` to run all validators
 * before submitting; it returns true if every field is valid.
 */
export function createFieldValidator() {
  const fields = [];

  function run(field, options) {
    const value = field.input.value;
    const message = field.validate(value, options || {});
    setFieldState(field, message);
    return !message;
  }

  function setFieldState(field, message) {
    if (message) {
      field.input.setAttribute("aria-invalid", "true");
      if (field.error) {
        field.error.textContent = message;
        field.error.hidden = false;
      }
      field.input.classList.add("invalid");
    } else {
      field.input.removeAttribute("aria-invalid");
      if (field.error) {
        field.error.textContent = "";
        field.error.hidden = true;
      }
      field.input.classList.remove("invalid");
    }
  }

  function attach(definition) {
    const field = { ...definition };
    if (!field.input || typeof field.validate !== "function") return;
    fields.push(field);
    field.input.addEventListener("blur", () => run(field));
    field.input.addEventListener("input", () => {
      if (field.input.classList.contains("invalid")) run(field);
    });
  }

  function validateAll(context = {}) {
    let ok = true;
    for (const field of fields) {
      if (!run(field, context)) ok = false;
    }
    return ok;
  }

  function reset() {
    for (const field of fields) {
      setFieldState(field, null);
    }
  }

  return { attach, validateAll, reset };
}

/* ---------- common validators ---------- */
export const required = (label) => (value) => {
  if (!value || !String(value).trim()) return `${label} is required.`;
  return null;
};

export const minLength = (label, n) => (value) => {
  if (value && value.length < n) return `${label} must be at least ${n} characters.`;
  return null;
};

export const noWhitespace = (label) => (value) => {
  if (value && /\s/.test(value)) return `${label} must not contain whitespace.`;
  return null;
};

export const integerMin = (label, min) => (value) => {
  if (value === "" || value == null) return null;
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n)) return `${label} must be an integer.`;
  if (n < min) return `${label} must be ${min} or greater.`;
  return null;
};

export function combine(...validators) {
  return (value, ctx) => {
    for (const v of validators) {
      const msg = v(value, ctx);
      if (msg) return msg;
    }
    return null;
  };
}
