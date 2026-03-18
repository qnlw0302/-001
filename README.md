# Inventory Management

This project is a small inventory management application with a Flask backend and a Vite-style frontend.

## What changed

- Backend moved from `http.server` to Flask
- API key protection added for create, update, and delete requests
- CORS and security headers added
- Environment-variable-based configuration added
- Logging enabled
- Product list now supports pagination
- Low stock logic is now fixed at a restock alert when stock is below `5`
- API tests added with Flask test client

## Project Structure

```text
inventory-management/
  main.py
  crud.py
  schemas.py
  requirements.txt
  .env.example
  README.md
  API_REFERENCE.md
  tests/
    test_api.py
  inventory-management-web/
    index.html
    package.json
    vite.config.js
    src/
      main.js
      style.css
```

## Product Schema

The backend uses the following schema objects in `schemas.py`:

- `Product`
- `ProductCreate`
- `ProductUpdate`

Fields:

- `id`
- `sku`
- `name`
- `stock_qty`
- `status`
- `needs_restock`
- `restock_threshold`

Status rules:

- `out`: stock is `0`
- `low`: stock is between `1` and `4`
- `ok`: stock is `5` or above

## Backend

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy environment settings:

```bash
cp .env.example .env
```

Run the backend:

```bash
python main.py
```

Open:

```text
http://127.0.0.1:5000
```

## Frontend

The frontend is in `inventory-management-web/`.

Run the Vite frontend:

```bash
cd inventory-management-web
npm install
npm run dev
```

Vite proxies `/api` requests to the Flask backend on port `5000`.

## API Notes

- `GET` endpoints do not require an API key
- `POST`, `PUT`, and `DELETE` require `X-API-Key`
- Product list supports `page`, `limit`, and `search`

Full endpoint details are in `API_REFERENCE.md`.

## Tests

Run tests with:

```bash
python -m unittest discover -s tests
```
