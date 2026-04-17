# API Reference

Base URL:

```text
http://127.0.0.1:5000
```

## Authentication

Session-based via cookie (`inventory_session`). Log in with `POST /api/auth/login` and the browser will receive an `HttpOnly` session cookie that is automatically sent on subsequent requests. `POST`, `PUT`, and `DELETE` on `/api/products` require a logged-in session. `DELETE` additionally requires the current user's password in the request body for confirmation.

The default admin account is seeded on first run from these environment variables (see `.env.example`):

```text
INVENTORY_ADMIN_USERNAME=admin
INVENTORY_ADMIN_PASSWORD=admin123
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

## POST /api/auth/login

Request:

```json
{
  "username": "admin",
  "password": "admin123",
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

## GET /api/products

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

Returns a single Product object, or `404` if not found.

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
{ "password": "admin123" }
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
