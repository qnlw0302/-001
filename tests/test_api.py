from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main import BASE_DIR, CSRF_HEADER, create_app


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "test-pass-123"


class CsrfTestClient:
    """Wraps Flask's test client to inject the CSRF header on mutating requests."""

    _MUTATING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    def __init__(self, app):
        self._client = app.test_client()
        self._csrf_token: str | None = None

    def _ensure_csrf_token(self) -> str:
        if self._csrf_token:
            return self._csrf_token
        response = self._client.get("/api/auth/csrf")
        if response.status_code != 200:
            raise RuntimeError("CSRF token endpoint failed.")
        token = response.get_json()["csrf_token"]
        self._csrf_token = token
        return token

    _SESSION_ROTATING_PATHS = {
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/register",
    }

    def _attach_csrf(self, method: str, kwargs: dict) -> dict:
        if method.upper() not in self._MUTATING_METHODS:
            return kwargs
        headers = dict(kwargs.get("headers") or {})
        if CSRF_HEADER not in headers:
            headers[CSRF_HEADER] = self._ensure_csrf_token()
        kwargs["headers"] = headers
        return kwargs

    def _maybe_invalidate_token(self, path: str) -> None:
        if path in self._SESSION_ROTATING_PATHS:
            self._csrf_token = None

    def get(self, path: str, *args, **kwargs):
        return self._client.get(path, *args, **kwargs)

    def post(self, path: str, *args, **kwargs):
        response = self._client.post(path, *args, **self._attach_csrf("POST", kwargs))
        self._maybe_invalidate_token(path)
        return response

    def put(self, path: str, *args, **kwargs):
        return self._client.put(path, *args, **self._attach_csrf("PUT", kwargs))

    def delete(self, path: str, *args, **kwargs):
        return self._client.delete(path, *args, **self._attach_csrf("DELETE", kwargs))

    def open(self, *args, **kwargs):
        return self._client.open(*args, **kwargs)


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
                # Rate-limit is generous enough not to interfere with the test
                # suite by default; specific tests that exercise it lower the
                # limit on their own app instance.
                "AUTH_RATE_LIMIT_MAX": 10_000,
            }
        )
        self.client = CsrfTestClient(self.app)

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

    def test_bootstrap_anonymous_with_seeded_admin(self) -> None:
        response = self.client.get("/api/auth/bootstrap")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsNone(body["user"])
        self.assertTrue(body["has_users"])

    def test_bootstrap_returns_logged_in_user(self) -> None:
        self.login()
        response = self.client.get("/api/auth/bootstrap")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsNotNone(body["user"])
        self.assertEqual(body["user"]["username"], ADMIN_USERNAME)
        self.assertTrue(body["has_users"])

    def test_bootstrap_reports_no_users_on_fresh_install(self) -> None:
        empty_dir = tempfile.TemporaryDirectory()
        self.addCleanup(empty_dir.cleanup)
        fresh_app = create_app(
            {
                "TESTING": True,
                "DB_PATH": str(Path(empty_dir.name) / "fresh.db"),
                "SECRET_KEY": "fresh-secret",
                "ADMIN_USERNAME": "",
                "ADMIN_PASSWORD": "",
                "FRONTEND_DIR": str(BASE_DIR / "inventory-management-web"),
                "LOG_LEVEL": "CRITICAL",
                "AUTH_RATE_LIMIT_MAX": 10_000,
            }
        )
        client = CsrfTestClient(fresh_app)
        response = client.get("/api/auth/bootstrap")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsNone(body["user"])
        self.assertFalse(body["has_users"])

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
            json={"name": "Mechanical Keyboard", "low_stock_threshold": 10},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["name"], "Mechanical Keyboard")
        # Stock didn't change (still 7), but the new threshold is 10, so it's low.
        self.assertEqual(payload["stock_qty"], 7)
        self.assertEqual(payload["status"], "low")

    def test_update_product_rejects_stock_qty(self) -> None:
        """PUT no longer accepts stock_qty — stock changes must go through movements."""
        self.login()
        created = self.create_product("SKU-NOSTOCK", "Thing", 5)
        product_id = created.get_json()["id"]

        response = self.client.put(
            "/api/products/%s" % product_id,
            json={"stock_qty": 99},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("movements", response.get_json()["error"])

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


class CsrfProtectionTestCase(_ApiTestMixin, unittest.TestCase):
    def test_post_without_csrf_header_is_rejected(self) -> None:
        # Use the raw client (no CSRF helper) to confirm the middleware fires.
        raw = self.app.test_client()
        response = raw.post(
            "/api/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.get_json()["error"])

    def test_csrf_token_endpoint_returns_token(self) -> None:
        response = self.client.get("/api/auth/csrf")
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["csrf_token"]
        self.assertIsInstance(token, str)
        self.assertGreaterEqual(len(token), 32)

    def test_get_requests_do_not_require_csrf(self) -> None:
        raw = self.app.test_client()
        response = raw.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)


class RateLimitTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DB_PATH": str(Path(self.temp_dir.name) / "test.db"),
                "SECRET_KEY": "test",
                "ADMIN_USERNAME": ADMIN_USERNAME,
                "ADMIN_PASSWORD": ADMIN_PASSWORD,
                "FRONTEND_DIR": str(BASE_DIR / "inventory-management-web"),
                "LOG_LEVEL": "CRITICAL",
                "AUTH_RATE_LIMIT_MAX": 3,
                "AUTH_RATE_LIMIT_WINDOW": 60,
            }
        )
        self.client = CsrfTestClient(self.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_repeated_logins_are_rate_limited(self) -> None:
        for _ in range(3):
            response = self.client.post(
                "/api/auth/login",
                json={"username": ADMIN_USERNAME, "password": "wrong-pass"},
            )
            self.assertIn(response.status_code, (401, 429))

        blocked = self.client.post(
            "/api/auth/login",
            json={"username": ADMIN_USERNAME, "password": "wrong-pass"},
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Too many", blocked.get_json()["error"])


class AccountLockoutTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DB_PATH": str(Path(self.temp_dir.name) / "test.db"),
                "SECRET_KEY": "test",
                "ADMIN_USERNAME": ADMIN_USERNAME,
                "ADMIN_PASSWORD": ADMIN_PASSWORD,
                "FRONTEND_DIR": str(BASE_DIR / "inventory-management-web"),
                "LOG_LEVEL": "CRITICAL",
                "AUTH_RATE_LIMIT_MAX": 10_000,
                "LOGIN_MAX_ATTEMPTS": 3,
                "LOGIN_LOCKOUT_SECONDS": 600,
            }
        )
        self.client = CsrfTestClient(self.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_account_locks_after_repeated_failed_logins(self) -> None:
        for _ in range(3):
            failed = self.client.post(
                "/api/auth/login",
                json={"username": ADMIN_USERNAME, "password": "wrong-pass"},
            )
            self.assertEqual(failed.status_code, 401)

        locked = self.client.post(
            "/api/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )
        self.assertEqual(locked.status_code, 429)
        payload = locked.get_json()
        self.assertIn("locked", payload["error"].lower())
        self.assertGreater(payload["retry_after_seconds"], 0)


class PasswordStrengthTestCase(_ApiTestMixin, unittest.TestCase):
    def test_register_rejects_common_password(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "password"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("common", response.get_json()["error"].lower())


class ExportTestCase(_ApiTestMixin, unittest.TestCase):
    def test_export_json_returns_all_products(self) -> None:
        self.login()
        self.create_product("E-1", "Alpha", 5)
        self.create_product("E-2", "Beta", 8)

        response = self.client.get("/api/products/export?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        payload = response.get_json()
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual({item["sku"] for item in payload["items"]}, {"E-1", "E-2"})

    def test_export_csv_returns_attachment(self) -> None:
        self.login()
        self.create_product("E-1", "Alpha", 5)
        response = self.client.get("/api/products/export?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))
        body = response.get_data(as_text=True)
        self.assertIn("sku", body.splitlines()[0])
        self.assertIn("E-1", body)

    def test_export_requires_login(self) -> None:
        response = self.client.get("/api/products/export?format=json")
        self.assertEqual(response.status_code, 401)

    def test_export_rejects_unknown_format(self) -> None:
        self.login()
        response = self.client.get("/api/products/export?format=xml")
        self.assertEqual(response.status_code, 400)


class AuditLogTestCase(_ApiTestMixin, unittest.TestCase):
    def test_audit_log_captures_product_changes(self) -> None:
        self.login()
        created = self.create_product("A-1", "Alpha", 5)
        product_id = created.get_json()["id"]

        self.client.put(
            "/api/products/%s" % product_id,
            json={"name": "Renamed"},
        )
        self.client.delete(
            "/api/products/%s" % product_id,
            json={"password": ADMIN_PASSWORD},
        )

        response = self.client.get("/api/auth/audit?limit=50")
        self.assertEqual(response.status_code, 200)
        events = response.get_json()["items"]
        actions = [event["action"] for event in events]
        self.assertIn("product.create", actions)
        self.assertIn("product.update", actions)
        self.assertIn("product.delete", actions)
        self.assertIn("auth.login", actions)


class ReadinessTestCase(_ApiTestMixin, unittest.TestCase):
    def test_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_ready_endpoint_returns_ready_when_db_reachable(self) -> None:
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")


class StockMovementTestCase(_ApiTestMixin, unittest.TestCase):
    def _create(self, stock_qty: int = 10):
        self.login()
        created = self.create_product("SKU-MV", "Widget", stock_qty)
        self.assertEqual(created.status_code, 201)
        return created.get_json()["id"]

    def _post_movement(self, product_id: int, payload: dict):
        return self.client.post(
            f"/api/products/{product_id}/movements",
            json=payload,
        )

    def test_receive_adds_to_stock(self) -> None:
        product_id = self._create(stock_qty=4)
        response = self._post_movement(product_id, {"type": "receive", "quantity": 6})
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["movement"]["movement_type"], "receive")
        self.assertEqual(body["movement"]["quantity_delta"], 6)
        self.assertEqual(body["movement"]["quantity_after"], 10)
        self.assertEqual(body["product"]["stock_qty"], 10)

    def test_return_adds_to_stock(self) -> None:
        product_id = self._create(stock_qty=2)
        response = self._post_movement(product_id, {"type": "return", "quantity": 3})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["product"]["stock_qty"], 5)

    def test_remove_subtracts_from_stock(self) -> None:
        product_id = self._create(stock_qty=8)
        response = self._post_movement(product_id, {"type": "remove", "quantity": 3})
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["movement"]["quantity_delta"], -3)
        self.assertEqual(body["product"]["stock_qty"], 5)

    def test_damaged_subtracts_from_stock(self) -> None:
        product_id = self._create(stock_qty=5)
        response = self._post_movement(product_id, {"type": "damaged", "quantity": 2})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["product"]["stock_qty"], 3)

    def test_adjust_sets_absolute_quantity(self) -> None:
        product_id = self._create(stock_qty=12)
        response = self._post_movement(product_id, {"type": "adjust", "quantity": 7})
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["movement"]["quantity_delta"], -5)
        self.assertEqual(body["movement"]["quantity_after"], 7)
        self.assertEqual(body["product"]["stock_qty"], 7)

    def test_adjust_to_zero_is_allowed(self) -> None:
        product_id = self._create(stock_qty=4)
        response = self._post_movement(product_id, {"type": "adjust", "quantity": 0})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["product"]["stock_qty"], 0)
        self.assertEqual(response.get_json()["product"]["status"], "out")

    def test_remove_rejected_when_would_go_negative(self) -> None:
        product_id = self._create(stock_qty=2)
        response = self._post_movement(product_id, {"type": "remove", "quantity": 5})
        self.assertEqual(response.status_code, 400)
        self.assertIn("in stock", response.get_json()["error"])

    def test_damaged_rejected_when_would_go_negative(self) -> None:
        product_id = self._create(stock_qty=1)
        response = self._post_movement(product_id, {"type": "damaged", "quantity": 2})
        self.assertEqual(response.status_code, 400)

    def test_zero_or_negative_quantity_rejected(self) -> None:
        product_id = self._create(stock_qty=5)
        for qty in (0, -3):
            response = self._post_movement(product_id, {"type": "receive", "quantity": qty})
            self.assertEqual(response.status_code, 400, msg=f"qty={qty}")

    def test_negative_adjust_rejected(self) -> None:
        product_id = self._create()
        response = self._post_movement(product_id, {"type": "adjust", "quantity": -1})
        self.assertEqual(response.status_code, 400)

    def test_unknown_movement_type_rejected(self) -> None:
        product_id = self._create()
        response = self._post_movement(product_id, {"type": "teleport", "quantity": 1})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Movement type", response.get_json()["error"])

    def test_movement_optional_note_persisted(self) -> None:
        product_id = self._create()
        response = self._post_movement(
            product_id, {"type": "receive", "quantity": 2, "note": "Truck arrival"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["movement"]["note"], "Truck arrival")

    def test_listing_returns_newest_first(self) -> None:
        product_id = self._create(stock_qty=0)
        self._post_movement(product_id, {"type": "receive", "quantity": 3})
        self._post_movement(product_id, {"type": "remove", "quantity": 1})
        self._post_movement(product_id, {"type": "adjust", "quantity": 9})

        listing = self.client.get(f"/api/products/{product_id}/movements")
        self.assertEqual(listing.status_code, 200)
        items = listing.get_json()["items"]
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["movement_type"], "adjust")
        self.assertEqual(items[1]["movement_type"], "remove")
        self.assertEqual(items[2]["movement_type"], "receive")

    def test_initial_stock_recorded_as_receive_movement(self) -> None:
        """Creating a product with stock_qty > 0 should leave a `receive` row in
        history so the ledger is complete from day one."""
        product_id = self._create(stock_qty=12)
        listing = self.client.get(f"/api/products/{product_id}/movements")
        items = listing.get_json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["movement_type"], "receive")
        self.assertEqual(items[0]["quantity_delta"], 12)
        self.assertEqual(items[0]["quantity_after"], 12)

    def test_initial_stock_zero_creates_no_seed_movement(self) -> None:
        self.login()
        created = self.create_product("SKU-ZERO", "Empty", 0)
        product_id = created.get_json()["id"]
        listing = self.client.get(f"/api/products/{product_id}/movements")
        self.assertEqual(listing.get_json()["items"], [])

    def test_other_user_cannot_record_movement(self) -> None:
        self.login()
        owner_product = self.create_product("SHARED", "Mine", 5).get_json()["id"]
        self.client.post("/api/auth/logout")

        register = self.client.post(
            "/api/auth/register",
            json={"username": "intruder", "password": "intruder-pass-123", "remember": False},
        )
        self.assertEqual(register.status_code, 201)

        response = self._post_movement(owner_product, {"type": "receive", "quantity": 1})
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_list_movements(self) -> None:
        self.login()
        owner_product = self.create_product("HIDDEN", "Mine", 5).get_json()["id"]
        self.client.post("/api/auth/logout")

        register = self.client.post(
            "/api/auth/register",
            json={"username": "peeker", "password": "peeker-pass-123", "remember": False},
        )
        self.assertEqual(register.status_code, 201)

        listing = self.client.get(f"/api/products/{owner_product}/movements")
        self.assertEqual(listing.status_code, 404)

    def test_movements_require_login(self) -> None:
        # No login() here.
        response = self.client.post(
            "/api/products/1/movements",
            json={"type": "receive", "quantity": 1},
        )
        self.assertEqual(response.status_code, 401)

    def test_movement_writes_audit_entry(self) -> None:
        product_id = self._create(stock_qty=5)
        self._post_movement(product_id, {"type": "remove", "quantity": 2})
        audit = self.client.get("/api/auth/audit?limit=50").get_json()["items"]
        actions = [event["action"] for event in audit]
        self.assertIn("stock.remove", actions)


if __name__ == "__main__":
    unittest.main()
