from __future__ import annotations

import sqlite3
from pathlib import Path

from schemas import LOW_STOCK_THRESHOLD, Product, ProductCreate, ProductUpdate


DB_PATH = Path(__file__).with_name("inventory.db")


def _connect(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _row_to_product(row: sqlite3.Row) -> Product:
    return Product(
        id=int(row["id"]),
        sku=str(row["sku"]),
        name=str(row["name"]),
        stock_qty=int(row["stock_qty"]),
        low_stock_threshold=LOW_STOCK_THRESHOLD,
    )


def init_db(db_path: str | Path = DB_PATH) -> None:
    with _connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                stock_qty INTEGER NOT NULL DEFAULT 0,
                low_stock_threshold INTEGER NOT NULL DEFAULT 5
            )
            """
        )

        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(products)").fetchall()
        }
        if "low_stock_threshold" not in columns:
            connection.execute(
                "ALTER TABLE products ADD COLUMN low_stock_threshold INTEGER NOT NULL DEFAULT 5"
            )

        connection.execute(
            "UPDATE products SET low_stock_threshold = ?",
            (LOW_STOCK_THRESHOLD,),
        )
        connection.commit()


def insert_product(data: ProductCreate, db_path: str | Path = DB_PATH) -> Product:
    with _connect(db_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM products WHERE sku = ? LIMIT 1",
            (data.sku,),
        ).fetchone()
        if exists:
            raise ValueError("SKU already exists.")

        cursor = connection.execute(
            """
            INSERT INTO products (sku, name, stock_qty, low_stock_threshold)
            VALUES (?, ?, ?, ?)
            """,
            (data.sku, data.name, data.stock_qty, LOW_STOCK_THRESHOLD),
        )
        connection.commit()

        row = connection.execute(
            "SELECT id, sku, name, stock_qty, low_stock_threshold FROM products WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    if row is None:
        raise RuntimeError("Product could not be loaded after insert.")
    return _row_to_product(row)


def get_product(product_id: int, db_path: str | Path = DB_PATH) -> Product | None:
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT id, sku, name, stock_qty, low_stock_threshold FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

    if row is None:
        return None
    return _row_to_product(row)


def get_product_by_sku(sku: str, db_path: str | Path = DB_PATH) -> Product | None:
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT id, sku, name, stock_qty, low_stock_threshold FROM products WHERE sku = ?",
            (sku.strip(),),
        ).fetchone()

    if row is None:
        return None
    return _row_to_product(row)


def update_product(product_id: int, data: ProductUpdate, db_path: str | Path = DB_PATH) -> Product:
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT id, sku, name, stock_qty, low_stock_threshold FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            raise LookupError("Product not found.")

        current = _row_to_product(row)
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
            SET sku = ?, name = ?, stock_qty = ?, low_stock_threshold = ?
            WHERE id = ?
            """,
            (next_sku, next_name, next_stock, LOW_STOCK_THRESHOLD, product_id),
        )
        connection.commit()

        updated_row = connection.execute(
            "SELECT id, sku, name, stock_qty, low_stock_threshold FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

    if updated_row is None:
        raise RuntimeError("Product could not be loaded after update.")
    return _row_to_product(updated_row)


def delete_product(product_id: int, db_path: str | Path = DB_PATH) -> bool:
    with _connect(db_path) as connection:
        cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
        connection.commit()
        return cursor.rowcount > 0


def list_all_products(search: str = "", db_path: str | Path = DB_PATH) -> list[Product]:
    with _connect(db_path) as connection:
        if search:
            like_value = f"%{search.strip().lower()}%"
            rows = connection.execute(
                """
                SELECT id, sku, name, stock_qty, low_stock_threshold
                FROM products
                WHERE lower(sku) LIKE ? OR lower(name) LIKE ?
                ORDER BY id DESC
                """,
                (like_value, like_value),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, sku, name, stock_qty, low_stock_threshold
                FROM products
                ORDER BY id DESC
                """
            ).fetchall()

    return [_row_to_product(row) for row in rows]
