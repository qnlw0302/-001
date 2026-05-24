"""Unit tests for desktop.py launcher helpers.

These are cross-platform — they don't open a webview window and don't touch the
real user-data dir. They exist so the launcher's plumbing (free port, persistent
secret, env configuration) can't quietly regress on either macOS or Windows.

The full GUI smoke test is the user-facing checklist in CLAUDE.md Stage 6.
"""

from __future__ import annotations

import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import desktop


class FreeLoopbackPortTests(unittest.TestCase):
    def test_returns_usable_loopback_port(self) -> None:
        port = desktop._free_loopback_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        self.assertLess(port, 65536)
        # Confirm the port is actually free right now — bind and release.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))

    def test_successive_calls_can_differ(self) -> None:
        # Not guaranteed to differ, but two calls should both produce valid ports.
        first = desktop._free_loopback_port()
        second = desktop._free_loopback_port()
        for port in (first, second):
            self.assertGreater(port, 0)
            self.assertLess(port, 65536)


class LoadOrCreateSecretTests(unittest.TestCase):
    def test_creates_secret_file_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            secret = desktop._load_or_create_secret(data_dir)
            self.assertIsInstance(secret, str)
            self.assertGreater(len(secret), 32, "Secret should be a strong token.")
            self.assertTrue((data_dir / "secret_key").is_file())

    def test_returns_same_secret_across_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            first = desktop._load_or_create_secret(data_dir)
            second = desktop._load_or_create_secret(data_dir)
            self.assertEqual(first, second)

    def test_recovers_when_existing_file_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            (data_dir / "secret_key").write_text("", encoding="utf-8")
            secret = desktop._load_or_create_secret(data_dir)
            self.assertGreater(len(secret), 32)
            self.assertEqual((data_dir / "secret_key").read_text(encoding="utf-8").strip(), secret)


class ConfigureEnvTests(unittest.TestCase):
    """The launcher must set the exact env vars create_app() reads — if these
    drift, the desktop build will silently fall back to dev defaults."""

    REQUIRED_KEYS = (
        "INVENTORY_HOST",
        "INVENTORY_PORT",
        "INVENTORY_DB_PATH",
        "INVENTORY_SECRET_KEY",
        "INVENTORY_ADMIN_USERNAME",
        "INVENTORY_ADMIN_PASSWORD",
    )

    def setUp(self) -> None:
        # Snapshot env so we can restore after each test.
        self._saved = {k: os.environ.get(k) for k in self.REQUIRED_KEYS + (
            "INVENTORY_LOG_LEVEL", "INVENTORY_CORS_ORIGIN",
            "INVENTORY_FRONTEND_DIR", "INVENTORY_LOG_DIR", "INVENTORY_DEBUG",
        )}
        for k in self._saved:
            os.environ.pop(k, None)

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_sets_required_inventory_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            log_dir = Path(tmp) / "logs"
            data_dir.mkdir()
            log_dir.mkdir()
            desktop._configure_env(data_dir, log_dir, 51234, "test-secret-token")

        self.assertEqual(os.environ["INVENTORY_HOST"], "127.0.0.1")
        self.assertEqual(os.environ["INVENTORY_PORT"], "51234")
        self.assertEqual(os.environ["INVENTORY_SECRET_KEY"], "test-secret-token")
        # DB path must point inside data_dir, not the source tree.
        self.assertIn("inventory.db", os.environ["INVENTORY_DB_PATH"])
        # Admin creds intentionally empty so no default user is seeded on fresh installs.
        self.assertEqual(os.environ["INVENTORY_ADMIN_USERNAME"], "")
        self.assertEqual(os.environ["INVENTORY_ADMIN_PASSWORD"], "")

    def test_log_level_defaults_to_warning_without_debug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            desktop._configure_env(Path(tmp), Path(tmp), 50000, "s")
        self.assertEqual(os.environ.get("INVENTORY_LOG_LEVEL"), "WARNING")

    def test_log_level_switches_to_debug_when_INVENTORY_DEBUG(self) -> None:
        os.environ["INVENTORY_DEBUG"] = "1"
        with tempfile.TemporaryDirectory() as tmp:
            desktop._configure_env(Path(tmp), Path(tmp), 50000, "s")
        self.assertEqual(os.environ.get("INVENTORY_LOG_LEVEL"), "DEBUG")

    def test_cors_origin_matches_loopback_port(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            desktop._configure_env(Path(tmp), Path(tmp), 49999, "s")
        self.assertEqual(os.environ["INVENTORY_CORS_ORIGIN"], "http://127.0.0.1:49999")


class ResourcePathTests(unittest.TestCase):
    def test_resolves_relative_to_module_dir_in_dev(self) -> None:
        # In dev (no PyInstaller bundle), _resource_path resolves against the repo root.
        result = desktop._resource_path("inventory-management-web/dist")
        self.assertTrue(result.is_absolute())
        # The repo root contains desktop.py itself.
        self.assertEqual(result.parent.name, "inventory-management-web")

    def test_resolves_relative_to_meipass_when_frozen(self) -> None:
        with patch.object(desktop.sys, "_MEIPASS", "/fake/bundle", create=True):
            result = desktop._resource_path("inventory-management-web/dist")
        self.assertTrue(str(result).startswith(str(Path("/fake/bundle"))))


if __name__ == "__main__":
    unittest.main()