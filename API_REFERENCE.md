# API Reference

Base URL:

```text
http://127.0.0.1:5000
```

## Authentication

Mutating endpoints require:

```http
X-API-Key: your-api-key
```

The local default key is:

```text
dev-inventory-key
```

unless overridden in `.env`.

## Product Object

```json
{
  "id": 1,
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 4,
  "status": "low",
  "needs_restock": true,
  "restock_threshold": 5
}
```

## GET /health

Response:

```json
{
  "status": "ok"
}
```

## GET /api/products

Query parameters:

- `search`
- `page`
- `limit`

Example:

```http
GET /api/products?search=note&page=1&limit=10
```

Response:

```json
{
  "items": [
    {
      "id": 1,
      "sku": "SKU-100",
      "name": "Notebook",
      "stock_qty": 4,
      "status": "low",
      "needs_restock": true,
      "restock_threshold": 5
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "pages": 1
  },
  "summary": {
    "total_products": 1,
    "low_stock_products": 1,
    "out_of_stock_products": 0,
    "restock_threshold": 5
  }
}
```

## GET /api/products/{id}

Response:

```json
{
  "id": 1,
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 4,
  "status": "low",
  "needs_restock": true,
  "restock_threshold": 5
}
```

## POST /api/products

Headers:

```http
Content-Type: application/json
X-API-Key: your-api-key
```

Request:

```json
{
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 4
}
```

## PUT /api/products/{id}

Headers:

```http
Content-Type: application/json
X-API-Key: your-api-key
```

Request:

```json
{
  "name": "Notebook Pro",
  "stock_qty": 8
}
```

## DELETE /api/products/{id}

Headers:

```http
X-API-Key: your-api-key
```

Success response:

```json
{
  "message": "Product deleted."
}
```

## Common Error Response

```json
{
  "error": "Missing or invalid API key."
}
```
