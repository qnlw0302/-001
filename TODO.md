# TODO

Living roadmap. Phase 0 is about knowing what we have; everything below is
what's missing or worth improving. Check items off as they land.

Legend: `[x]` done · `[ ]` open · `[~]` partially done

---

## Snapshot (as of Phase 2)

- **Auth model:** session cookie, server-side. Register + login + logout +
  update profile + change password all work. CSRF token required on all
  cookie-auth mutations. Rate limit on `/api/auth/login` and
  `/api/auth/register`. Account lockout after 5 consecutive failed logins.
- **Tenancy:** per-user. `products.user_id` FK + `UNIQUE(user_id, sku)`.
  Cross-tenant access returns `404` (no ownership leakage).
- **Service layer:** routes call `services.InventoryService` instead of
  touching `sqlite3.Connection` directly. Audit events are written from the
  service layer.
- **Audit log:** every product create/update/delete, login, logout,
  register, profile/password change is recorded in `audit_log` and exposed
  via `GET /api/auth/audit`.
- **Frontend:** split into `src/lib/*` (api, dom, state, toast, validation,
  focus-trap) and `src/views/*` (login, register, inventory, modals). Inline
  field-level validation, loading/disabled submit states, toast
  notifications, modal focus trap, aria-live regions, polished empty states,
  mobile layout tweaks. Export-to-CSV button.
- **Tests:** 53 API tests green against a temp SQLite file, including
  coverage for CSRF, rate limiting, account lockout, password strength,
  export, audit log, readiness, and tenancy isolation.
- **Deploy:** still local-dev only. Flask now serves
  `inventory-management-web/dist` automatically when a build exists, so
  `npm run build` followed by `python main.py` runs the whole app from a
  single process. No Dockerfile, no CI.

---

## Frontend

- [x] Login view with remember-me
- [x] Register view (username + password + confirm + remember)
- [x] Inventory dashboard (list, stats, search, pagination)
- [x] Product create / update form
- [x] Per-product low-stock threshold input
- [x] Custom fields editor (add/remove rows)
- [x] Delete-with-password confirmation modal
- [x] Edit-profile modal (change username)
- [x] Change-password modal
- [x] XSS-safe rendering via `escapeHtml`
- [x] Inline field-level validation
- [x] Loading / disabled states on submit buttons
- [x] Toast notification system (`src/lib/toast.js`) replacing per-panel divs
      for non-blocking feedback
- [x] Split `main.js` into view + lib modules
      (`src/views/{login,register,inventory,modals}.js`,
      `src/lib/{api,dom,state,toast,validation,focus-trap}.js`)
- [x] Accessibility pass: focus trap in modals, aria-live on messages,
      proper `<label for>` bindings, `role="dialog" aria-modal="true"`
- [x] Visual polish on empty states and mobile layout (responsive hero,
      table scroll wrapper, larger toast on mobile)
- [x] Serve built assets in production (Flask auto-picks
      `inventory-management-web/dist` when it exists; override via
      `INVENTORY_FRONTEND_DIR`)
- [x] CSRF token fetched on bootstrap and refreshed on session rotation
- [x] CSV export button (calls `/api/products/export?format=csv` and
      triggers a download)

## Backend

- [x] Flask app factory, test-config injection
- [x] Session auth with `login_required` decorator
- [x] Password hashing (pbkdf2:sha256 via Werkzeug)
- [x] Input validation in `schemas.py` (required/optional/MISSING sentinel)
- [x] Structured error handlers (ApiError, ValueError, LookupError, sqlite3)
- [x] Pagination + search + summary on list endpoint
- [x] Custom fields validation (key/value limits, type whitelist)
- [x] `POST /api/auth/register` endpoint (+ schema + tests)
- [x] `PUT /api/auth/me` (update username, confirmed by password)
- [x] `POST /api/auth/change-password`
- [x] All `/api/products` endpoints require login and are scoped by `user_id`
- [x] Rate limiting on login + register (in-memory sliding window keyed by
      client IP; tunable via env)
- [x] CSRF token for cookie-auth mutations (`/api/auth/csrf` issues a
      session-bound token; middleware checks `X-CSRF-Token` on all
      protected methods)
- [x] Audit log table for create/update/delete actions, plus auth events.
      Exposed via `GET /api/auth/audit`
- [x] Replace ad-hoc `.env` loader with `python-dotenv` (falls back to the
      old parser if the dep is not installed)
- [x] Typed service layer (`services.InventoryService`) so routes stop
      touching `sqlite3.Connection` directly
- [x] `GET /api/products/export?format=json|csv` (streams CSV; JSON returns
      a single document)
- [x] `GET /ready` endpoint that checks DB connectivity (`/health` stays
      as a pure liveness probe)

## Database

- [x] `products` table with custom_fields JSON + per-product threshold
- [x] `users` table with password_hash
- [x] Additive migrations (`ALTER TABLE ADD COLUMN` idempotent on startup)
- [x] Add `user_id` foreign key to `products` for per-user isolation
- [x] One-shot migration: pre-Phase-1 `products` rebuilt on startup, old rows
      assigned to the seed admin, `UNIQUE(user_id, sku)` enforced
- [x] `PRAGMA foreign_keys = ON` set on every connection
- [x] Expression indexes on `products(user_id, lower(sku))` and
      `products(user_id, lower(name))` (created on every startup, idempotent)
- [x] `audit_log` table + `idx_audit_log_user`
- [x] `users.failed_login_count` + `users.locked_until` columns added via
      additive migration
- [x] Backup / export endpoint (CSV or JSON dump)
- [x] Seed / fixture script for dev data (`python seed.py` /
      `python seed.py --reset`)
- [ ] Formal migration tool (Alembic-lite or hand-rolled versioned scripts)
      once schema changes get non-additive

## Security

- [x] HttpOnly session cookie, SameSite=Lax
- [x] CSP, X-Frame-Options, Referrer-Policy, nosniff headers
- [x] CORS restricted to a single origin with credentials
- [x] Password required again for deletes, profile edits, and password changes
- [x] Cross-tenant access returns 404 (no ownership leakage)
- [x] Passwords stored hashed (pbkdf2:sha256), verified with `secrets.compare_digest` via Werkzeug
- [x] Rate limiting (login, register)
- [x] CSRF token for POST/PUT/DELETE (defense in depth beyond SameSite)
- [x] Account lockout after repeated failed logins
- [x] Password strength policy: minimum length + common-password blocklist
      (top ~40 entries; swap for zxcvbn-style estimator before production)
- [x] `Secure` cookie flag driven by env (already wired, documented in
      `.env.example`)
- [ ] Secrets management in production (stop relying on `.env` on disk)
- [ ] Security review / threat model write-up

## Deployment

- [ ] Dockerfile for backend (gunicorn, non-root user, multi-stage)
- [ ] docker-compose for dev (backend + built frontend + volume for db)
- [ ] CI: run `python -m unittest` and `vite build` on every push
- [ ] Production-grade WSGI server (gunicorn / uvicorn-behind-nginx)
- [ ] HTTPS termination story (reverse proxy + cert)
- [ ] Move from SQLite to Postgres for multi-process deployments
- [ ] Observability: request logs to file, basic metrics endpoint
- [ ] Deploy target picked (Fly.io / Render / self-hosted VM / …)

---

## Phase 0 exit checklist

- [x] README reflects current code (session auth, custom fields, threshold)
- [x] `.env.example` documents every supported variable
- [x] Database schema documented in README
- [x] API list documented in README + `API_REFERENCE.md`
- [x] TODO.md split by area
- [x] Local run verified (`python -m unittest discover -s tests` → all green)

## Phase 1 exit checklist (MVP core)

- [x] Register, login, logout, "me", update profile, change password all work
- [x] Passwords stored hashed (verified with a DB-level test)
- [x] Users have a stable unique `id`
- [x] Session lives in an HttpOnly signed cookie; logout clears it
- [x] Every `/api/products` endpoint refuses anonymous callers (tested)
- [x] Each user sees only their own products (tested across two users)
- [x] Same SKU can exist for two different users (tested)
- [x] Migration from Phase-0 DB to Phase-1 schema verified against real `inventory.db`
- [x] Frontend has a register view and two account-settings modals

## Phase 2 exit checklist (hardening)

- [x] CSRF token required on all cookie-auth mutations (tested via raw client)
- [x] Login + register rate-limited per IP (tested)
- [x] Account lockout after configurable consecutive failures (tested)
- [x] Common-password blocklist enforced on register + change-password (tested)
- [x] Audit log records auth + product mutations (tested)
- [x] `/ready` does a DB ping; `/health` stays cheap (tested)
- [x] `GET /api/products/export?format=json|csv` returns a download (tested)
- [x] Routes use the service layer; only services touch `sqlite3.Connection`
- [x] Frontend split into lib + views; toast + inline validation + focus trap
- [x] Production-mode Flask serves `inventory-management-web/dist` by default
