from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main import BASE_DIR, create_app


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "test-pass-123"


class InventoryApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_inventory.db"
        self.app = create_app(
            {
                "TESTING": True,
                "DB_PATH": str(self.db_path),
                "SECRET_KEY": "test-secret",
                "ADMIN_USERNAME": ADMIN_USERNAME,
                "ADMIN_PASSWORD": ADMIN_PASSWORD,
                "FRONTEND_DIR": str(BASE_DIR / "inventory-management-web"),
                "LOG_LEVEL": "CRITICAL",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def login(self, username: str = ADMIN_USERNAME, password: str = ADMIN_PASSWORD, remember: bool = False):
        return self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password, "remember": remember},
        )

    def create_product(self, sku: str, name: str, stock_qty: int):
        return self.client.post(
            "/api/products",
            json={"sku": sku, "name": name, "stock_qty": stock_qty},
        )

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_me_requires_login(self) -> None:
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(response.get_json()["user"])

    def test_login_with_valid_credentials(self) -> None:
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["username"], ADMIN_USERNAME)

        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["user"]["username"], ADMIN_USERNAME)

    def test_login_with_invalid_credentials(self) -> None:
        response = self.login(password="wrong")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid", response.get_json()["error"])

    def test_logout_clears_session(self) -> None:
        self.login()
        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200)

        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 401)

    def test_insert_requires_login(self) -> None:
        response = self.create_product("SKU-1", "Mouse", 6)
        self.assertEqual(response.status_code, 401)

    def test_insert_and_get_product(self) -> None:
        self.login()
        created = self.create_product("SKU-1", "Mouse", 6)
        self.assertEqual(created.status_code, 201)
        product_id = created.get_json()["id"]

        fetched = self.client.get("/api/products/%s" % product_id)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["name"], "Mouse")
        self.assertEqual(fetched.get_json()["status"], "ok")

    def test_low_stock_flag_when_quantity_is_below_five(self) -> None:
        self.login()
        response = self.create_product("SKU-LOW", "Cable", 4)
        payload = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["status"], "low")
        self.assertTrue(payload["needs_restock"])

    def test_list_products_supports_pagination(self) -> None:
        self.login()
        for index in range(12):
            response = self.create_product("SKU-%s" % index, "Item %s" % index, index + 1)
            self.assertEqual(response.status_code, 201)

        page_one = self.client.get("/api/products?page=1&limit=10")
        page_two = self.client.get("/api/products?page=2&limit=10")

        self.assertEqual(page_one.status_code, 200)
        self.assertEqual(page_two.status_code, 200)
        self.assertEqual(len(page_one.get_json()["items"]), 10)
        self.assertEqual(len(page_two.get_json()["items"]), 2)
        self.assertEqual(page_two.get_json()["pagination"]["pages"], 2)

    def test_update_product_changes_fields(self) -> None:
        self.login()
        created = self.create_product("SKU-2", "Keyboard", 7)
        product_id = created.get_json()["id"]

        response = self.client.put(
            "/api/products/%s" % product_id,
            json={"name": "Mechanical Keyboard", "stock_qty": 3},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["name"], "Mechanical Keyboard")
        self.assertEqual(payload["status"], "low")

    def test_delete_requires_login(self) -> None:
        response = self.client.delete("/api/products/1", json={"password": ADMIN_PASSWORD})
        self.assertEqual(response.status_code, 401)

    def test_delete_requires_password_confirmation(self) -> None:
        self.login()
        created = self.create_product("SKU-3", "Monitor", 8)
        product_id = created.get_json()["id"]

        without_password = self.client.delete("/api/products/%s" % product_id, json={})
        self.assertEqual(without_password.status_code, 400)

        wrong_password = self.client.delete(
            "/api/products/%s" % product_id,
            json={"password": "wrong"},
        )
        self.assertEqual(wrong_password.status_code, 403)
        self.assertIn("Password", wrong_password.get_json()["error"])

    def test_delete_product_removes_record(self) -> None:
        self.login()
        created = self.create_product("SKU-4", "Chair", 2)
        product_id = created.get_json()["id"]

        deleted = self.client.delete(
            "/api/products/%s" % product_id,
            json={"password": ADMIN_PASSWORD},
        )
        missing = self.client.get("/api/products/%s" % product_id)

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(missing.status_code, 404)

    def test_product_defaults_when_threshold_not_provided(self) -> None:
        self.login()
        response = self.create_product("SKU-DEF", "Box", 10)
        payload = response.get_json()
        self.assertIsNone(payload["low_stock_threshold"])
        self.assertEqual(payload["restock_threshold"], 5)
        self.assertEqual(payload["custom_fields"], {})

    def test_custom_threshold_controls_status(self) -> None:
        self.login()
        response = self.client.post(
            "/api/products",
            json={
                "sku": "SKU-CT",
                "name": "Fragile",
                "stock_qty": 6,
                "low_stock_threshold": 10,
            },
        )
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["low_stock_threshold"], 10)
        self.assertEqual(payload["restock_threshold"], 10)
        self.assertEqual(payload["status"], "low")
        self.assertTrue(payload["needs_restock"])

    def test_custom_fields_roundtrip(self) -> None:
        self.login()
        response = self.client.post(
            "/api/products",
            json={
                "sku": "SKU-CF",
                "name": "Widget",
                "stock_qty": 8,
                "custom_fields": {
                    "category": "Electronics",
                    "supplier": "Acme",
                    "fragile": True,
                    "weight_kg": 1.5,
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        product_id = response.get_json()["id"]

        fetched = self.client.get("/api/products/%s" % product_id).get_json()
        self.assertEqual(fetched["custom_fields"]["category"], "Electronics")
        self.assertEqual(fetched["custom_fields"]["supplier"], "Acme")
        self.assertEqual(fetched["custom_fields"]["fragile"], True)
        self.assertEqual(fetched["custom_fields"]["weight_kg"], 1.5)

    def test_update_can_clear_threshold(self) -> None:
        self.login()
        created = self.client.post(
            "/api/products",
            json={"sku": "SKU-UT", "name": "Item", "stock_qty": 4, "low_stock_threshold": 10},
        )
        product_id = created.get_json()["id"]
        self.assertEqual(created.get_json()["low_stock_threshold"], 10)

        cleared = self.client.put(
            "/api/products/%s" % product_id,
            json={"low_stock_threshold": None},
        )
        self.assertEqual(cleared.status_code, 200)
        payload = cleared.get_json()
        self.assertIsNone(payload["low_stock_threshold"])
        self.assertEqual(payload["restock_threshold"], 5)

    def test_update_without_threshold_key_leaves_it_unchanged(self) -> None:
        self.login()
        created = self.client.post(
            "/api/products",
            json={"sku": "SKU-KEEP", "name": "Item", "stock_qty": 4, "low_stock_threshold": 8},
        )
        product_id = created.get_json()["id"]

        updated = self.client.put(
            "/api/products/%s" % product_id,
            json={"name": "Renamed"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["low_stock_threshold"], 8)

    def test_list_low_stock_count_uses_per_product_threshold(self) -> None:
        self.login()
        # Stock=6 with default threshold 5 would be OK, but with custom 10 it's low.
        self.client.post(
            "/api/products",
            json={"sku": "SKU-A", "name": "A", "stock_qty": 6, "low_stock_threshold": 10},
        )
        # Stock=6 with default threshold is OK and should not be counted.
        self.client.post(
            "/api/products",
            json={"sku": "SKU-B", "name": "B", "stock_qty": 6},
        )
        summary = self.client.get("/api/products").get_json()["summary"]
        self.assertEqual(summary["low_stock_products"], 1)
        self.assertEqual(summary["total_products"], 2)

    def test_invalid_custom_fields_rejected(self) -> None:
        self.login()
        response = self.client.post(
            "/api/products",
            json={
                "sku": "SKU-BAD",
                "name": "Bad",
                "stock_qty": 1,
                "custom_fields": {"nested": {"not": "allowed"}},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Custom field", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
