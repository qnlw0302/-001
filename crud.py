from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from schemas import (
    LOW_STOCK_THRESHOLD,
    MISSING,
    Product,
    ProductCreate,
    ProductUpdate,
    User,
)


PathLike = Union[str, Path]

PRODUCT_COLUMNS = "id, sku, name, stock_qty, low_stock_threshold, custom_fields"


def connect_db(db_path: PathLike) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _parse_custom_fields(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
    return {}


def _row_to_product(row: sqlite3.Row) -> Product:
    threshold_value = row["low_stock_threshold"] if "low_stock_threshold" in row.keys() else None
    custom_raw = row["custom_fields"] if "custom_fields" in row.keys() else None
    return Product(
        id=int(row["id"]),
        sku=str(row["sku"]),
        name=str(row["name"]),
        stock_qty=int(row["stock_qty"]),
        low_stock_threshold=int(threshold_value) if threshold_value is not None else None,
        custom_fields=_parse_custom_fields(custom_raw),
    )


def _row_to_user(row: sqlite3.Row) -> User:
    return User(id=int(row["id"]), username=str(row["username"]))


def _table_columns(connection: sqlite3.Connection, table: str) -> List[str]:
    return [str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]


def init_db(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            stock_qty INTEGER NOT NULL DEFAULT 0,
            low_stock_threshold INTEGER,
            custom_fields TEXT NOT NULL DEFAULT '{}'
        )
        """
    )

    existing = _table_columns(connection, "products")
    if "low_stock_threshold" not in existing:
        connection.execute("ALTER TABLE products ADD COLUMN low_stock_threshold INTEGER")
    if "custom_fields" not in existing:
        connection.execute(
            "ALTER TABLE products ADD COLUMN custom_fields TEXT NOT NULL DEFAULT '{}'"
        )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def create_user(connection: sqlite3.Connection, username: str, password_hash: str) -> User:
    cursor = connection.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    connection.commit()
    row = connection.execute(
        "SELECT id, username FROM users WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:
        raise RuntimeError("User could not be loaded after insert.")
    return _row_to_user(row)


def get_user_by_username(connection: sqlite3.Connection, username: str) -> Optional[Dict[str, Any]]:
    row = connection.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username.strip(),),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": int(row["id"]),
        "username": str(row["username"]),
        "password_hash": str(row["password_hash"]),
    }


def get_user_by_id(connection: sqlite3.Connection, user_id: int) -> Optional[User]:
    row = connection.execute(
        "SELECT id, username FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_user(row)


def get_password_hash(connection: sqlite3.Connection, user_id: int) -> Optional[str]:
    row = connection.execute(
        "SELECT password_hash FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return str(row["password_hash"])


def insert_product(connection: sqlite3.Connection, data: ProductCreate) -> Product:
    exists = connection.execute(
        "SELECT 1 FROM products WHERE sku = ? LIMIT 1",
        (data.sku,),
    ).fetchone()
    if exists:
        raise ValueError("SKU already exists.")

    cursor = connection.execute(
        """
        INSERT INTO products (sku, name, stock_qty, low_stock_threshold, custom_fields)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.sku,
            data.name,
            data.stock_qty,
            data.low_stock_threshold,
            json.dumps(data.custom_fields),
        ),
    )
    connection.commit()

    row = connection.execute(
        f"SELECT {PRODUCT_COLUMNS} FROM products WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Product could not be loaded after insert.")
    return _row_to_product(row)


def get_product(connection: sqlite3.Connection, product_id: int) -> Optional[Product]:
    row = connection.execute(
        f"SELECT {PRODUCT_COLUMNS} FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_product(row)


def get_product_by_sku(connection: sqlite3.Connection, sku: str) -> Optional[Product]:
    row = connection.execute(
        f"SELECT {PRODUCT_COLUMNS} FROM products WHERE sku = ?",
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

    if data.low_stock_threshold is MISSING:
        next_threshold = current.low_stock_threshold
    else:
        next_threshold = data.low_stock_threshold

    if data.custom_fields is MISSING:
        next_custom = current.custom_fields
    else:
        next_custom = data.custom_fields

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
        SET sku = ?, name = ?, stock_qty = ?, low_stock_threshold = ?, custom_fields = ?
        WHERE id = ?
        """,
        (next_sku, next_name, next_stock, next_threshold, json.dumps(next_custom), product_id),
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


def _build_where(conditions: List[str]) -> str:
    return "WHERE " + " AND ".join(conditions) if conditions else ""


def list_products(
    connection: sqlite3.Connection,
    search: str = "",
    page: int = 1,
    limit: int = 20,
) -> Dict[str, Any]:
    page = max(1, int(page))
    limit = max(1, min(100, int(limit)))
    offset = (page - 1) * limit

    search_conditions: List[str] = []
    search_params: List[Any] = []
    if search:
        like_value = "%%%s%%" % search.strip().lower()
        search_conditions.append("(lower(sku) LIKE ? OR lower(name) LIKE ?)")
        search_params.extend([like_value, like_value])

    search_where = _build_where(search_conditions)
    search_params_tuple = tuple(search_params)

    total = connection.execute(
        "SELECT COUNT(*) AS count FROM products %s" % search_where,
        search_params_tuple,
    ).fetchone()["count"]

    rows = connection.execute(
        f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products
        {search_where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        search_params_tuple + (limit, offset),
    ).fetchall()

    low_where = _build_where(
        search_conditions + ["stock_qty > 0", "stock_qty < COALESCE(low_stock_threshold, ?)"]
    )
    low_stock_count = connection.execute(
        "SELECT COUNT(*) AS count FROM products %s" % low_where,
        search_params_tuple + (LOW_STOCK_THRESHOLD,),
    ).fetchone()["count"]

    out_where = _build_where(search_conditions + ["stock_qty <= 0"])
    out_of_stock_count = connection.execute(
        "SELECT COUNT(*) AS count FROM products %s" % out_where,
        search_params_tuple,
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
