# API Reference

Base URL:

```text
http://127.0.0.1:5000
```

## Product Schema

Response object:

```json
{
  "id": 1,
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 3,
  "low_stock_threshold": 5,
  "status": "low"
}
```

Field description:

- `id`: product id
- `sku`: product SKU
- `name`: product name
- `stock_qty`: current stock quantity
- `low_stock_threshold`: fixed to `5`
- `status`: `ok`, `low`, or `out`

## 1. Health Check

### Request

```http
GET /health
```

### Response

```json
{
  "status": "ok"
}
```

## 2. Insert Product

### Request

```http
POST /api/products
Content-Type: application/json
```

```json
{
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 3
}
```

### Success Response

Status: `201 Created`

```json
{
  "id": 1,
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 3,
  "low_stock_threshold": 5,
  "status": "low"
}
```

### Error Response

Status: `400 Bad Request`

```json
{
  "error": "SKU already exists."
}
```

## 3. Get Product

### Request

```http
GET /api/products/1
```

### Success Response

Status: `200 OK`

```json
{
  "id": 1,
  "sku": "SKU-100",
  "name": "Notebook",
  "stock_qty": 3,
  "low_stock_threshold": 5,
  "status": "low"
}
```

### Error Response

Status: `404 Not Found`

```json
{
  "error": "Product not found."
}
```

## 4. Update Product

### Request

```http
PUT /api/products/1
Content-Type: application/json
```

```json
{
  "name": "Notebook Pro",
  "stock_qty": 8
}
```

### Success Response

Status: `200 OK`

```json
{
  "id": 1,
  "sku": "SKU-100",
  "name": "Notebook Pro",
  "stock_qty": 8,
  "low_stock_threshold": 5,
  "status": "ok"
}
```

### Error Response

Status: `400 Bad Request`

```json
{
  "error": "At least one field is required for update."
}
```

## 5. Delete Product

### Request

```http
DELETE /api/products/1
```

### Success Response

Status: `200 OK`

```json
{
  "message": "Product deleted."
}
```

### Error Response

Status: `404 Not Found`

```json
{
  "error": "Product not found."
}
```

## 6. List All Products

### Request

```http
GET /api/products
```

### Optional Search

```http
GET /api/products?search=note
```

### Success Response

Status: `200 OK`

```json
[
  {
    "id": 2,
    "sku": "SKU-200",
    "name": "Monitor",
    "stock_qty": 12,
    "low_stock_threshold": 5,
    "status": "ok"
  },
  {
    "id": 1,
    "sku": "SKU-100",
    "name": "Notebook",
    "stock_qty": 3,
    "low_stock_threshold": 5,
    "status": "low"
  }
]
```

## Validation Rules

- `sku` is required when creating a product
- `name` is required when creating a product
- `stock_qty` must be an integer
- `stock_qty` must be `>= 0`
- `sku` max length is `64`
- `name` max length is `200`
- `low_stock_threshold` is not user-configurable in this version and is always `5`
