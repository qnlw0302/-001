# API Reference

Base URL:

```text
http://127.0.0.1:5000
```

## Authentication

Session-based via cookie (`inventory_session`). Log in with `POST /api/auth/login`
or create an account with `POST /api/auth/register`; the browser will receive
an `HttpOnly` session cookie that is automatically sent on subsequent requests.
**All `/api/products` endpoints require a logged-in session** and return only
the calling user's own products. `DELETE` additionally requires the current
user's password in the request body for confirmation.

The default admin account is seeded on first run from these environment
variables (see `.env.example`):

```text
INVENTORY_ADMIN_USERNAME=admin
INVENTORY_ADMIN_PASSWORD=change-me-admin-password
```

Change these before deploying anywhere real.

## Product Object

```json
{
  "id": 1,
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 4,
  "status": "low",
  "needs_restock": true,
  "low_stock_threshold": null,
  "restock_threshold": 5,
  "default_restock_threshold": 5,
  "custom_fields": {
    "category": "Stationery",
    "supplier": "Acme"
  }
}
```

Field notes:

- `low_stock_threshold` — per-product override. `null` means "use the system default".
- `restock_threshold` — the effective threshold used to compute `status` and `needs_restock` for this product.
- `default_restock_threshold` — the current system default (`LOW_STOCK_THRESHOLD`), shown for UI reference.
- `custom_fields` — user-defined key/value pairs. Keys are strings (max 64 chars). Values may be strings (max 500 chars), numbers, booleans, or `null`. Max 50 entries per product.

## GET /health

```json
{ "status": "ok" }
```

## POST /api/auth/register

Creates a new user and starts a session. Registration is open — no existing
account required.

Request:

```json
{
  "username": "alice",
  "password": "at-least-six-chars",
  "remember": true
}
```

Validation:

- `username` — 3–64 chars, no whitespace.
- `password` — 6–128 chars.
- `remember` — optional, defaults to `false`.

Response (201):

```json
{
  "user": { "id": 2, "username": "alice" }
}
```

Errors:

- `400` — validation failed (bad username / short password / …)
- `409 Username already taken.`

## POST /api/auth/login

Request:

```json
{
  "username": "admin",
  "password": "change-me-admin-password",
  "remember": true
}
```

Response (200):

```json
{
  "user": { "id": 1, "username": "admin" }
}
```

Errors:

- `401 Invalid username or password.`

When `remember` is `true` the session cookie persists for 30 days. When `false` it is cleared when the browser closes.

## POST /api/auth/logout

Clears the session. Returns:

```json
{ "message": "Logged out." }
```

## GET /api/auth/me

Returns the logged-in user, or `401` with `{ "user": null }` when not authenticated.

## PUT /api/auth/me

Requires login. Updates the calling user's username. The current password must
be supplied as a confirmation step.

Request:

```json
{
  "username": "new-name",
  "current_password": "current-pw"
}
```

Responses:

- `200 { "user": { "id": 1, "username": "new-name" } }`
- `400` validation failed
- `403 Current password is incorrect.`
- `409 Username already taken.`

Passing the same username the user already has is a no-op and returns the
current user unchanged.

## POST /api/auth/change-password

Requires login. Changes the calling user's password. The session remains valid
after the change.

Request:

```json
{
  "current_password": "current-pw",
  "new_password": "at-least-six-chars"
}
```

Responses:

- `200 { "message": "Password changed." }`
- `400` — validation failed, or new password equals current
- `403 Current password is incorrect.`

## GET /api/products

Requires login. Only the calling user's products are returned.

Query parameters: `search`, `page`, `limit`.

Response:

```json
{
  "items": [/* Product objects */],
  "pagination": { "page": 1, "limit": 10, "total": 1, "pages": 1 },
  "summary": {
    "total_products": 1,
    "low_stock_products": 1,
    "out_of_stock_products": 0,
    "restock_threshold": 5
  }
}
```

## GET /api/products/{id}

Requires login. Returns a single Product object, or `404` if the product does
not exist **or belongs to another user** (the response is intentionally
indistinguishable in the two cases to avoid leaking ownership information).

## POST /api/products

Requires login.

Request:

```json
{
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 4,
  "low_stock_threshold": 10,
  "custom_fields": {
    "category": "Stationery",
    "supplier": "Acme"
  }
}
```

`low_stock_threshold` and `custom_fields` are optional.

## PUT /api/products/{id}

Requires login.

Request (partial update — only send keys you want to change):

```json
{
  "name": "Notebook Pro",
  "stock_qty": 8,
  "low_stock_threshold": null,
  "custom_fields": { "category": "Stationery", "color": "blue" }
}
```

Semantics:

- A key **omitted** from the request leaves the stored value unchanged.
- `low_stock_threshold: null` **clears** the override (the system default applies again).
- `custom_fields: {}` clears all custom fields. Any value you send fully **replaces** the stored object.

## DELETE /api/products/{id}

Requires login **and** password re-confirmation in the request body.

Request:

```json
{ "password": "change-me-admin-password" }
```

Responses:

- `200 { "message": "Product deleted." }`
- `401 Authentication required.`
- `403 Password does not match.`
- `404 Product not found.`

## Common Error Response

```json
{ "error": "Authentication required." }
```
