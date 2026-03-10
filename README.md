# Inventory Management

This project is a simple inventory management web application with a Python backend and a Vite-style frontend.

## Features

- Create a `Product` schema
- Insert product
- Get product
- Update product
- Delete product
- List all products
- Low stock warning with a fixed threshold of `5`

## Project Structure

```text
inventory-management/
  main.py
  crud.py
  schemas.py
  inventory.db
  inventory-management-web/
    index.html
    package.json
    vite.config.js
    src/
      main.js
      style.css
```

## Product Schema

The backend uses three schema classes defined in `schemas.py`:

- `Product`: complete product object returned by the backend
- `ProductCreate`: payload schema for creating a product
- `ProductUpdate`: payload schema for updating a product

Schema fields:

- `id`: integer
- `sku`: string, required, max length `64`
- `name`: string, required, max length `200`
- `stock_qty`: integer, must be `>= 0`
- `low_stock_threshold`: fixed to `5`
- `status`: computed field, one of `ok`, `low`, `out`

Status rules:

- `out`: `stock_qty <= 0`
- `low`: `stock_qty <= 5`
- `ok`: `stock_qty > 5`

## Backend

The backend is implemented in `main.py`. It uses:

- `http.server` for HTTP handling
- `sqlite3` for database storage
- `crud.py` for data access
- `schemas.py` for schema validation

### Run the backend

```bash
python3 main.py
```

After the server starts, open:

```text
http://127.0.0.1:5000
```

The backend also serves the frontend files from `inventory-management-web/`.

## Frontend

The frontend lives in `inventory-management-web/` and follows a Vite project structure.

### Files

- `index.html`: app entry
- `src/main.js`: UI logic and API calls
- `src/style.css`: page styles
- `package.json`: Vite scripts
- `vite.config.js`: local dev proxy config

### Run with Vite

This requires Node.js and npm to be installed first.

```bash
cd inventory-management-web
npm install
npm run dev
```

Default Vite dev URL:

```text
http://127.0.0.1:5173
```

The Vite config proxies `/api` requests to the Python backend at `http://127.0.0.1:5000`.

## API Summary

The API is documented in `API_REFERENCE.md`.

Main endpoints:

- `GET /health`
- `GET /api/products`
- `GET /api/products/{id}`
- `POST /api/products`
- `PUT /api/products/{id}`
- `DELETE /api/products/{id}`

## Database

Data is stored in `inventory.db` using a single `products` table.

Table fields:

- `id`
- `sku`
- `name`
- `stock_qty`
- `low_stock_threshold`

## Notes

- The low stock threshold is always `5`.
- The backend can run without any third-party Python package.
- The frontend uses plain JavaScript with a Vite-compatible structure.
