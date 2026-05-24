# Inventory Management

A small inventory management application with a Flask backend (SQLite) and a
Vanilla-JS + Vite frontend. Session-cookie authentication, per-product custom
fields, and per-product low-stock thresholds.

## Stack at a Glance

| Layer     | Tech                                   |
|-----------|----------------------------------------|
| Backend   | Python 3, Flask, Werkzeug              |
| Database  | SQLite (single file, `inventory.db`)   |
| Frontend  | Vanilla JS + Vite 5                    |
| Auth      | Server-side session cookie (HttpOnly)  |
| Tests     | `unittest` + Flask test client         |

## Project Structure

```text
inventory-management/
  main.py                      # Flask app factory, routes, CSRF, rate-limit, error handlers, static serving
  auth.py                      # Session auth, password hashing, seed admin
  crud.py                      # SQLite access + product/user/audit/lockout queries
  services.py                  # Typed service layer wrapping crud + audit + lockout
  schemas.py                   # Dataclasses + request payload validation + common-password blocklist
  seed.py                      # Optional demo-data seed script
  requirements.txt
  .env.example
  README.md
  API_REFERENCE.md
  docs/
    USER_MANUAL_EN.md        # English user manual
    USER_MANUAL_ZH.md        # Chinese user manual
  TODO.md                      # Roadmap split by Frontend / Backend / DB / Security / Deploy
  tests/
    test_api.py                # API tests driven by Flask test client
  inventory-management-web/
    index.html
    package.json
    vite.config.js
    src/
      main.js                  # Bootstrap: wires views + CSRF + session restore
      style.css
      lib/                     # api, dom, state, toast, validation, focus-trap
      views/                   # login.js, register.js, inventory.js, modals.js
    dist/                      # `npm run build` output (Flask serves this in prod)
```

## Responsibilities

- **Backend (`main.py`, `auth.py`, `crud.py`, `services.py`, `schemas.py`)**
  - Exposes JSON endpoints under `/api/*`.
  - Owns session-cookie auth, CSRF protection, per-IP rate limiting,
    account lockout, password hashing (pbkdf2-sha256), input validation,
    and all SQLite access (only `services.py` and `crud.py` touch the DB).
  - Records an audit-log entry for every auth event and product mutation.
  - Serves the built frontend in production via `serve_frontend` (with path
    traversal protection). Falls back to the source dir when no build is
    present.
- **Frontend (`inventory-management-web/`)**
  - Split into `lib/` (api, dom, state, toast, validation, focus-trap) and
    `views/` (login, register, inventory, modals). `main.js` is the
    bootstrap.
  - Talks to the backend with `fetch(..., { credentials: "include" })` so the
    session cookie rides along, fetches a CSRF token on first mutation, and
    re-fetches automatically on session rotation.
  - In development, Vite proxies `/api` and `/health` to `http://127.0.0.1:5000`.
  - Includes an English/Chinese language selector. The selected language is
    remembered in browser local storage.

## User Manuals

- [English User Manual](docs/USER_MANUAL_EN.md)
- [中文用户手册](docs/USER_MANUAL_ZH.md)

## Database Schema

SQLite, auto-created on first run by [`init_db`](crud.py#L65).

### `products`

| Column                | Type      | Notes                                      |
|-----------------------|-----------|--------------------------------------------|
| `id`                  | INTEGER   | PK, autoincrement                          |
| `sku`                 | TEXT      | NOT NULL, UNIQUE                           |
| `name`                | TEXT      | NOT NULL                                   |
| `stock_qty`           | INTEGER   | NOT NULL, default 0                        |
| `low_stock_threshold` | INTEGER   | Nullable. `NULL` = use system default (5)  |
| `custom_fields`       | TEXT      | JSON object, NOT NULL, default `'{}'`      |

### `products` columns (continued)

- `user_id` — NOT NULL, FK → `users(id)` ON DELETE CASCADE.
- `UNIQUE(user_id, sku)` — SKU is unique *per user*. Two different users may
  both have `SKU-100`.

### `users`

| Column                | Type    | Notes                                     |
|-----------------------|---------|-------------------------------------------|
| `id`                  | INTEGER | PK, autoincrement                         |
| `username`            | TEXT    | NOT NULL, UNIQUE                          |
| `password_hash`       | TEXT    | NOT NULL, pbkdf2:sha256                   |
| `created_at`          | TEXT    | default `CURRENT_TIMESTAMP`               |
| `failed_login_count`  | INTEGER | NOT NULL, default 0 (lockout counter)     |
| `locked_until`        | TEXT    | nullable ISO timestamp; non-null = locked |

### `audit_log`

| Column        | Type    | Notes                                            |
|---------------|---------|--------------------------------------------------|
| `id`          | INTEGER | PK, autoincrement                                |
| `user_id`     | INTEGER | FK → `users(id)` ON DELETE SET NULL              |
| `action`      | TEXT    | e.g. `product.create`, `auth.login`              |
| `entity_type` | TEXT    | nullable (`product`, `user`)                     |
| `entity_id`   | INTEGER | nullable                                         |
| `details`     | TEXT    | JSON, nullable                                   |
| `ip_address`  | TEXT    | nullable                                         |
| `created_at`  | TEXT    | default `CURRENT_TIMESTAMP`                      |

### Indexes

- `idx_products_user_sku_lower` on `products(user_id, lower(sku))`
- `idx_products_user_name_lower` on `products(user_id, lower(name))`
- `idx_audit_log_user` on `audit_log(user_id, created_at DESC)`

### Migration from older schemas

Databases created before Phase 1 did not have `user_id`. On startup, the app
auto-rebuilds the `products` table, assigns all existing rows to the seed
admin user, and swaps the new schema in. Phase-2 columns
(`users.failed_login_count`, `users.locked_until`) and the `audit_log` table
are added via additive migrations on startup. All of this is idempotent.

## Product Status Rules

Derived in Python ([`Product.status`](schemas.py#L191)), never stored:

- `out`  — `stock_qty <= 0`
- `low`  — `0 < stock_qty < effective_threshold`
- `ok`   — `stock_qty >= effective_threshold`

`effective_threshold` is `low_stock_threshold` if set, otherwise
`LOW_STOCK_THRESHOLD = 5`.

## Running Locally

### 1. Backend

```bash
pip install -r requirements.txt
cp .env.example .env   # edit INVENTORY_SECRET_KEY and admin password
python main.py
```

Backend listens on `http://127.0.0.1:5000` by default and seeds the admin user
from `INVENTORY_ADMIN_USERNAME` / `INVENTORY_ADMIN_PASSWORD` on first run.

### 2. Frontend (development)

```bash
cd inventory-management-web
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` and `/health` to the Flask
server on port 5000.

### 3. Frontend (production)

Build the SPA once; Flask serves it automatically on `/` when `dist/` is
present:

```bash
cd inventory-management-web
npm run build
cd ..
python main.py        # now serves the SPA + API on http://127.0.0.1:5000
```

Override the served directory with `INVENTORY_FRONTEND_DIR` if you build to
a different location.

### 4. Creating users

Registration is open — click **Create one** on the login page, or
`POST /api/auth/register`. The seed admin from `.env` is a convenience for the
first login only; any user can register and will see an empty inventory of
their own.

### 5. Demo data (optional)

```bash
python seed.py            # add demo users + products
python seed.py --reset    # wipe demo users' products first, then re-seed
```

Demo accounts: `demo / demo-pass-1234`, `warehouse / warehouse-1234`.

## Authentication

- `POST /api/auth/register` with `{username, password, remember}` creates a
  user and starts a session.
- `POST /api/auth/login` with the same shape signs an existing user in.
- Both set a session cookie named `inventory_session` (HttpOnly, SameSite=Lax).
  `remember: true` persists the cookie for 30 days; otherwise it ends with the
  browser session.
- `POST /api/auth/logout` clears the cookie.
- `GET /api/auth/me` returns the current user, or 401 for anonymous callers.
- `PUT /api/auth/me` updates username (requires current password).
- `POST /api/auth/change-password` rotates the password (requires current
  password; session stays valid).
- **Every** `/api/products` endpoint requires a valid session. Requests for a
  product belonging to another user return `404` to avoid leaking ownership.
- `DELETE /api/products/<id>` additionally requires the current user's password
  in the request body as a second confirmation.

Passwords are hashed with `pbkdf2:sha256` (Werkzeug default) and never stored
or logged in plaintext. Common passwords (top-40 leaks list) are rejected at
registration and password-change time.

### CSRF

All mutating `/api/*` requests (`POST`, `PUT`, `DELETE`, `PATCH`) require
an `X-CSRF-Token` header. The token is bound to the current session — fetch
it from `GET /api/auth/csrf` and re-fetch after login/logout/register since
those rotate the session. The frontend handles all of this automatically.

### Rate limiting and account lockout

- `POST /api/auth/login` and `POST /api/auth/register` are per-IP rate-limited
  (`INVENTORY_AUTH_RATE_LIMIT_MAX` requests in
  `INVENTORY_AUTH_RATE_LIMIT_WINDOW` seconds; default 10/60). Excess
  requests get `429 Too many requests`.
- After `INVENTORY_LOGIN_MAX_ATTEMPTS` consecutive failed logins (default 5)
  the account is locked for `INVENTORY_LOGIN_LOCKOUT_SECONDS` (default 900).
  A successful login resets the counter.

## Security Headers

Every response sets (see [`after_request`](main.py#L127)):

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- `Content-Security-Policy: default-src 'self'; ...`

CORS is restricted to `INVENTORY_CORS_ORIGIN` (default `http://127.0.0.1:5173`)
and only opens on `/api/*`.

## API

Full endpoint reference is in [API_REFERENCE.md](API_REFERENCE.md). Summary:

| Method | Path                           | Auth             | Purpose                                   |
|--------|--------------------------------|------------------|-------------------------------------------|
| GET    | `/health`                      | none             | Liveness probe                            |
| GET    | `/ready`                       | none             | Readiness probe (pings the DB)            |
| GET    | `/api/auth/csrf`               | none             | Issue/refresh the session CSRF token      |
| POST   | `/api/auth/register`           | none             | Create user, set session                  |
| POST   | `/api/auth/login`              | none             | Log in, set session cookie                |
| POST   | `/api/auth/logout`             | none             | Clear session                             |
| GET    | `/api/auth/me`                 | 401 if anonymous | Current user                              |
| PUT    | `/api/auth/me`                 | session + pw     | Update username                           |
| POST   | `/api/auth/change-password`    | session + pw     | Rotate password                           |
| GET    | `/api/auth/audit`              | session          | Caller's recent audit-log entries         |
| GET    | `/api/products`                | session          | List own products (+ pagination + stats)  |
| GET    | `/api/products/export`         | session          | Stream own products as JSON or CSV        |
| GET    | `/api/products/<id>`           | session          | Fetch own product                         |
| POST   | `/api/products`                | session          | Create                                    |
| PUT    | `/api/products/<id>`           | session          | Partial update                            |
| DELETE | `/api/products/<id>`           | session + pw     | Delete with password confirmation         |

## Tests

```bash
python -m unittest discover -s tests
```

Tests use Flask's test client against a temp SQLite file and a fresh seed admin
per test.
