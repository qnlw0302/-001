"""Populate the local SQLite database with demo users and products.

Usage:
    python seed.py            # add demo data without touching existing rows
    python seed.py --reset    # delete demo users/products first, then seed

Demo accounts:
    demo / demo-pass-1234       (regular user with a small catalog)
    warehouse / warehouse-1234  (regular user with low/out-of-stock variety)

The seed only runs against the DB path resolved from `.env` /
`INVENTORY_DB_PATH`. It will not touch a production database unless that
database is what `.env` points at.
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

from main import BASE_DIR, create_app
from auth import hash_password
from crud import (
    connect_db,
    create_user,
    delete_product,
    get_user_by_username,
    insert_product,
    iter_all_products,
)
from schemas import ProductCreate


DEMO_USERS: List[Tuple[str, str]] = [
    ("demo", "demo-pass-1234"),
    ("warehouse", "warehouse-1234"),
]

DEMO_PRODUCTS = {
    "demo": [
        ProductCreate(
            sku="DEMO-001",
            name="Wireless Mouse",
            stock_qty=24,
            low_stock_threshold=10,
            custom_fields={"category": "Peripherals", "supplier": "Acme"},
        ),
        ProductCreate(
            sku="DEMO-002",
            name="Mechanical Keyboard",
            stock_qty=8,
            low_stock_threshold=10,
            custom_fields={"category": "Peripherals", "switch": "brown"},
        ),
        ProductCreate(
            sku="DEMO-003",
            name="USB-C Cable, 2m",
            stock_qty=3,
            custom_fields={"category": "Cables", "length_m": 2},
        ),
    ],
    "warehouse": [
        ProductCreate(
            sku="WH-CHAIR",
            name="Office Chair",
            stock_qty=0,
            custom_fields={"category": "Furniture", "color": "black"},
        ),
        ProductCreate(
            sku="WH-DESK",
            name="Standing Desk",
            stock_qty=12,
            low_stock_threshold=4,
            custom_fields={"category": "Furniture"},
        ),
        ProductCreate(
            sku="WH-MONITOR",
            name="27\" Monitor",
            stock_qty=2,
            low_stock_threshold=5,
            custom_fields={"category": "Displays", "resolution": "2560x1440"},
        ),
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete demo users' products before re-seeding.",
    )
    args = parser.parse_args()

    app = create_app()
    connection = connect_db(app.config["DB_PATH"])
    try:
        for username, password in DEMO_USERS:
            existing = get_user_by_username(connection, username)
            if existing is None:
                user = create_user(connection, username, hash_password(password))
                user_id = user.id
                print(f"+ created user {username!r} (id={user_id})")
            else:
                user_id = existing["id"]
                print(f"- user {username!r} already exists (id={user_id})")

            if args.reset:
                removed = 0
                for product in list(iter_all_products(connection, user_id)):
                    if delete_product(connection, user_id, product.id):
                        removed += 1
                if removed:
                    print(f"  reset: removed {removed} existing products")

            for product_data in DEMO_PRODUCTS.get(username, []):
                try:
                    insert_product(connection, user_id, product_data)
                    print(f"  + product {product_data.sku!r} ({product_data.name})")
                except ValueError as error:
                    print(f"  - skipping {product_data.sku!r}: {error}")
    finally:
        connection.close()

    print(f"\nSeed complete. DB: {app.config['DB_PATH']}")
    print("Log in with one of the demo users above to explore the app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
