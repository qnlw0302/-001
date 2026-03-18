from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from schemas import LOW_STOCK_THRESHOLD, Product, ProductCreate, ProductUpdate


PathLike = Union[str, Path]


def connect_db(db_path: PathLike) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _row_to_product(row: sqlite3.Row) -> Product:
    return Product(
        id=int(row["id"]),
        sku=str(row["sku"]),
        name=str(row["name"]),
        stock_qty=int(row["stock_qty"]),
    )


def _table_has_column(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute("PRAGMA table_info(%s)" % table_name).fetchall()
    return any(row["name"] == column_name for row in rows)


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def init_db(connection: sqlite3.Connection) -> None:
    if _table_exists(connection, "products") and _table_has_column(connection, "products", "low_stock_threshold"):
        connection.execute("ALTER TABLE products RENAME TO products_legacy")
        connection.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                stock_qty INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            INSERT INTO products (id, sku, name, stock_qty)
            SELECT id, sku, name, stock_qty
            FROM products_legacy
            """
        )
        connection.execute("DROP TABLE products_legacy")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            stock_qty INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    connection.commit()


def insert_product(connection: sqlite3.Connection, data: ProductCreate) -> Product:
    exists = connection.execute(
        "SELECT 1 FROM products WHERE sku = ? LIMIT 1",
        (data.sku,),
    ).fetchone()
    if exists:
        raise ValueError("SKU already exists.")

    cursor = connection.execute(
        """
        INSERT INTO products (sku, name, stock_qty)
        VALUES (?, ?, ?)
        """,
        (data.sku, data.name, data.stock_qty),
    )
    connection.commit()

    row = connection.execute(
        "SELECT id, sku, name, stock_qty FROM products WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Product could not be loaded after insert.")
    return _row_to_product(row)


def get_product(connection: sqlite3.Connection, product_id: int) -> Optional[Product]:
    row = connection.execute(
        "SELECT id, sku, name, stock_qty FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_product(row)


def get_product_by_sku(connection: sqlite3.Connection, sku: str) -> Optional[Product]:
    row = connection.execute(
        "SELECT id, sku, name, stock_qty FROM products WHERE sku = ?",
        (sku.strip(),),
    ).fetchone()
    if row is None:
        return None
    return _row_to_product(row)


def update_product(connection: sqlite3.Connection, product_id: int, data: ProductUpdate) -> Product:
    current = get_product(connection, product_id)
    if current is None:
        raise LookupError("Product not found.")

    next_sku = data.sku if data.sku is not None else current.sku
    next_name = data.name if data.name is not None else current.name
    next_stock = data.stock_qty if data.stock_qty is not None else current.stock_qty

    if next_sku != current.sku:
        exists = connection.execute(
            "SELECT 1 FROM products WHERE sku = ? AND id != ? LIMIT 1",
            (next_sku, product_id),
        ).fetchone()
        if exists:
            raise ValueError("SKU already exists.")

    connection.execute(
        """
        UPDATE products
        SET sku = ?, name = ?, stock_qty = ?
        WHERE id = ?
        """,
        (next_sku, next_name, next_stock, product_id),
    )
    connection.commit()

    updated = get_product(connection, product_id)
    if updated is None:
        raise RuntimeError("Product could not be loaded after update.")
    return updated


def delete_product(connection: sqlite3.Connection, product_id: int) -> bool:
    cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
    connection.commit()
    return cursor.rowcount > 0


def _build_search_clause(search: str) -> Tuple[str, Tuple[Any, ...]]:
    if not search:
        return "", ()
    like_value = "%%%s%%" % search.strip().lower()
    return "WHERE lower(sku) LIKE ? OR lower(name) LIKE ?", (like_value, like_value)


def list_products(
    connection: sqlite3.Connection,
    search: str = "",
    page: int = 1,
    limit: int = 20,
) -> Dict[str, Any]:
    page = max(1, int(page))
    limit = max(1, min(100, int(limit)))
    offset = (page - 1) * limit

    where_clause, params = _build_search_clause(search)

    total = connection.execute(
        "SELECT COUNT(*) AS count FROM products %s" % where_clause,
        params,
    ).fetchone()["count"]

    rows = connection.execute(
        """
        SELECT id, sku, name, stock_qty
        FROM products
        %s
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """ % where_clause,
        params + (limit, offset),
    ).fetchall()

    low_stock_count = connection.execute(
        "SELECT COUNT(*) AS count FROM products %s%s" % (
            where_clause,
            " AND stock_qty > 0 AND stock_qty < ?" if where_clause else "WHERE stock_qty > 0 AND stock_qty < ?",
        ),
        params + (LOW_STOCK_THRESHOLD,),
    ).fetchone()["count"]

    out_of_stock_count = connection.execute(
        "SELECT COUNT(*) AS count FROM products %s%s" % (
            where_clause,
            " AND stock_qty <= 0" if where_clause else "WHERE stock_qty <= 0",
        ),
        params,
    ).fetchone()["count"]

    items = [_row_to_product(row).to_dict() for row in rows]
    total_pages = max(1, int(math.ceil(float(total) / float(limit)))) if total else 1

    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": total_pages,
        },
        "summary": {
            "total_products": total,
            "low_stock_products": low_stock_count,
            "out_of_stock_products": out_of_stock_count,
            "restock_threshold": LOW_STOCK_THRESHOLD,
        },
    }
