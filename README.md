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
  main.py                      # Flask app factory, routes, error handlers, static serving
  auth.py                      # Session auth, password hashing, seed admin
  crud.py                      # SQLite access + product/user queries
  schemas.py                   # Dataclasses + request payload validation
  requirements.txt
  .env.example
  README.md
  API_REFERENCE.md
  TODO.md                      # Roadmap split by Frontend / Backend / DB / Security / Deploy
  tests/
    test_api.py                # API tests driven by Flask test client
  inventory-management-web/
    index.html
    package.json
    vite.config.js
    src/
      main.js                  # All UI: login view, inventory view, modals
      style.css
```

## Responsibilities

- **Backend (`main.py`, `auth.py`, `crud.py`, `schemas.py`)**
  - Exposes JSON endpoints under `/api/*`.
  - Owns session-cookie auth, password hashing (pbkdf2-sha256), input
    validation, and all SQLite access.
  - Serves the built frontend in production via `serve_frontend` (with path
    traversal protection).
- **Frontend (`inventory-management-web/`)**
  - Renders login and inventory views into `#app` without any framework.
  - Talks to the backend with `fetch(..., { credentials: "include" })` so the
    session cookie rides along.
  - In development, Vite proxies `/api` and `/health` to `http://127.0.0.1:5000`.

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

| Column          | Type    | Notes                         |
|-----------------|---------|-------------------------------|
| `id`            | INTEGER | PK, autoincrement             |
| `username`      | TEXT    | NOT NULL, UNIQUE              |
| `password_hash` | TEXT    | NOT NULL, pbkdf2:sha256       |
| `created_at`    | TEXT    | default `CURRENT_TIMESTAMP`   |

### Migration from Phase 0

Databases created before Phase 1 did not have `user_id`. On startup, the app
auto-rebuilds the `products` table, assigns all existing rows to the seed
admin user, and swaps the new schema in. This runs once and is idempotent.

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

### 3. Creating users

Registration is open — click **Create one** on the login page, or
`POST /api/auth/register`. The seed admin from `.env` is a convenience for the
first login only; any user can register and will see an empty inventory of
their own.

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
or logged in plaintext.

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
| POST   | `/api/auth/register`           | none             | Create user, set session                  |
| POST   | `/api/auth/login`              | none             | Log in, set session cookie                |
| POST   | `/api/auth/logout`             | none             | Clear session                             |
| GET    | `/api/auth/me`                 | 401 if anonymous | Current user                              |
| PUT    | `/api/auth/me`                 | session + pw     | Update username                           |
| POST   | `/api/auth/change-password`    | session + pw     | Rotate password                           |
| GET    | `/api/products`                | session          | List own products (+ pagination + stats)  |
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
