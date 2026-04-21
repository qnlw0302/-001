from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main import BASE_DIR, create_app


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "test-pass-123"


class _ApiTestMixin:
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


class InventoryApiTestCase(_ApiTestMixin, unittest.TestCase):

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

    def test_list_products_requires_login(self) -> None:
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, 401)

    def test_get_single_product_requires_login(self) -> None:
        response = self.client.get("/api/products/1")
        self.assertEqual(response.status_code, 401)


class RegistrationTestCase(_ApiTestMixin, unittest.TestCase):
    def test_register_creates_user_and_starts_session(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "alice-pass-123"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["user"]["username"], "alice")

        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["user"]["username"], "alice")

    def test_register_rejects_duplicate_username(self) -> None:
        first = self.client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "alice-pass-123"},
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "other-pass-456"},
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("taken", second.get_json()["error"])

    def test_register_rejects_short_password(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"username": "bob", "password": "short"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("characters", response.get_json()["error"])

    def test_register_rejects_whitespace_username(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"username": "bad name", "password": "decent-pass"},
        )
        self.assertEqual(response.status_code, 400)

    def test_password_is_stored_hashed(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "carol", "password": "carol-pass-123"},
        )
        import sqlite3
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?", ("carol",)
        ).fetchone()
        connection.close()
        self.assertIsNotNone(row)
        self.assertNotEqual(row["password_hash"], "carol-pass-123")
        self.assertTrue(row["password_hash"].startswith("pbkdf2:"))


class ChangePasswordTestCase(_ApiTestMixin, unittest.TestCase):
    def test_change_password_requires_login(self) -> None:
        response = self.client.post(
            "/api/auth/change-password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "new-pass-123"},
        )
        self.assertEqual(response.status_code, 401)

    def test_change_password_rejects_wrong_current(self) -> None:
        self.login()
        response = self.client.post(
            "/api/auth/change-password",
            json={"current_password": "wrong", "new_password": "new-pass-123"},
        )
        self.assertEqual(response.status_code, 403)

    def test_change_password_rejects_same_as_current(self) -> None:
        self.login()
        response = self.client.post(
            "/api/auth/change-password",
            json={"current_password": ADMIN_PASSWORD, "new_password": ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 400)

    def test_change_password_allows_login_with_new_password(self) -> None:
        self.login()
        response = self.client.post(
            "/api/auth/change-password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "new-pass-123"},
        )
        self.assertEqual(response.status_code, 200)

        self.client.post("/api/auth/logout")

        old_login = self.login(password=ADMIN_PASSWORD)
        self.assertEqual(old_login.status_code, 401)

        new_login = self.login(password="new-pass-123")
        self.assertEqual(new_login.status_code, 200)


class UpdateProfileTestCase(_ApiTestMixin, unittest.TestCase):
    def test_update_profile_changes_username(self) -> None:
        self.login()
        response = self.client.put(
            "/api/auth/me",
            json={"username": "admin2", "current_password": ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["username"], "admin2")

        self.client.post("/api/auth/logout")
        login_with_new = self.login(username="admin2")
        self.assertEqual(login_with_new.status_code, 200)

    def test_update_profile_requires_current_password(self) -> None:
        self.login()
        response = self.client.put(
            "/api/auth/me",
            json={"username": "admin2", "current_password": "wrong"},
        )
        self.assertEqual(response.status_code, 403)

    def test_update_profile_rejects_taken_username(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={"username": "taken", "password": "taken-pass-123"},
        )
        self.client.post("/api/auth/logout")
        self.login()

        response = self.client.put(
            "/api/auth/me",
            json={"username": "taken", "current_password": ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 409)

    def test_update_profile_same_username_is_noop(self) -> None:
        self.login()
        response = self.client.put(
            "/api/auth/me",
            json={"username": ADMIN_USERNAME, "current_password": ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["username"], ADMIN_USERNAME)


class TenancyIsolationTestCase(_ApiTestMixin, unittest.TestCase):
    def _register(self, username: str, password: str):
        return self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )

    def test_users_only_see_their_own_products(self) -> None:
        self._register("alice", "alice-pass-123")
        self.client.post("/api/products", json={"sku": "A-1", "name": "Alice Widget", "stock_qty": 5})
        self.client.post("/api/auth/logout")

        self._register("bob", "bob-pass-12345")
        self.client.post("/api/products", json={"sku": "B-1", "name": "Bob Gadget", "stock_qty": 3})

        listing = self.client.get("/api/products").get_json()
        skus = [item["sku"] for item in listing["items"]]
        self.assertEqual(skus, ["B-1"])
        self.assertEqual(listing["summary"]["total_products"], 1)

    def test_user_cannot_fetch_anothers_product(self) -> None:
        self._register("alice", "alice-pass-123")
        created = self.client.post(
            "/api/products", json={"sku": "A-1", "name": "Alice Widget", "stock_qty": 5}
        )
        product_id = created.get_json()["id"]
        self.client.post("/api/auth/logout")

        self._register("bob", "bob-pass-12345")
        response = self.client.get("/api/products/%s" % product_id)
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_update_anothers_product(self) -> None:
        self._register("alice", "alice-pass-123")
        created = self.client.post(
            "/api/products", json={"sku": "A-1", "name": "Alice Widget", "stock_qty": 5}
        )
        product_id = created.get_json()["id"]
        self.client.post("/api/auth/logout")

        self._register("bob", "bob-pass-12345")
        response = self.client.put(
            "/api/products/%s" % product_id,
            json={"name": "Hijacked"},
        )
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_anothers_product(self) -> None:
        self._register("alice", "alice-pass-123")
        created = self.client.post(
            "/api/products", json={"sku": "A-1", "name": "Alice Widget", "stock_qty": 5}
        )
        product_id = created.get_json()["id"]
        self.client.post("/api/auth/logout")

        self._register("bob", "bob-pass-12345")
        response = self.client.delete(
            "/api/products/%s" % product_id,
            json={"password": "bob-pass-12345"},
        )
        self.assertEqual(response.status_code, 404)

    def test_same_sku_allowed_across_different_users(self) -> None:
        self._register("alice", "alice-pass-123")
        alice_create = self.client.post(
            "/api/products", json={"sku": "SHARED", "name": "Alice", "stock_qty": 5}
        )
        self.assertEqual(alice_create.status_code, 201)
        self.client.post("/api/auth/logout")

        self._register("bob", "bob-pass-12345")
        bob_create = self.client.post(
            "/api/products", json={"sku": "SHARED", "name": "Bob", "stock_qty": 7}
        )
        self.assertEqual(bob_create.status_code, 201)


if __name__ == "__main__":
    unittest.main()
