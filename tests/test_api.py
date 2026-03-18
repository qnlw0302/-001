from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main import BASE_DIR, create_app


class InventoryApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_inventory.db"
        self.app = create_app(
            {
                "TESTING": True,
                "DB_PATH": str(self.db_path),
                "API_KEY": "test-key",
                "FRONTEND_DIR": str(BASE_DIR / "inventory-management-web"),
                "LOG_LEVEL": "CRITICAL",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def auth_headers(self):
        return {"X-API-Key": "test-key"}

    def create_product(self, sku: str, name: str, stock_qty: int):
        return self.client.post(
            "/api/products",
            json={"sku": sku, "name": name, "stock_qty": stock_qty},
            headers=self.auth_headers(),
        )

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_insert_and_get_product(self) -> None:
        created = self.create_product("SKU-1", "Mouse", 6)
        self.assertEqual(created.status_code, 201)
        product_id = created.get_json()["id"]

        fetched = self.client.get("/api/products/%s" % product_id)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["name"], "Mouse")
        self.assertEqual(fetched.get_json()["status"], "ok")

    def test_low_stock_flag_when_quantity_is_below_five(self) -> None:
        response = self.create_product("SKU-LOW", "Cable", 4)
        payload = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload["status"], "low")
        self.assertTrue(payload["needs_restock"])

    def test_list_products_supports_pagination(self) -> None:
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
        created = self.create_product("SKU-2", "Keyboard", 7)
        product_id = created.get_json()["id"]

        response = self.client.put(
            "/api/products/%s" % product_id,
            json={"name": "Mechanical Keyboard", "stock_qty": 3},
            headers=self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["name"], "Mechanical Keyboard")
        self.assertEqual(payload["status"], "low")

    def test_delete_requires_api_key(self) -> None:
        created = self.create_product("SKU-3", "Monitor", 8)
        product_id = created.get_json()["id"]

        response = self.client.delete("/api/products/%s" % product_id)
        self.assertEqual(response.status_code, 401)
        self.assertIn("API key", response.get_json()["error"])

    def test_delete_product_removes_record(self) -> None:
        created = self.create_product("SKU-4", "Chair", 2)
        product_id = created.get_json()["id"]

        deleted = self.client.delete(
            "/api/products/%s" % product_id,
            headers=self.auth_headers(),
        )
        missing = self.client.get("/api/products/%s" % product_id)

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
