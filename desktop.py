"""Desktop launcher: serves the Flask app on a loopback port and opens a pywebview window.

The launcher owns three things `main.py` does not:
  1. Resolving an OS-appropriate app-data directory (via platformdirs) so the SQLite
     file, secret key, and logs live outside the source tree.
  2. Generating + persisting a SECRET_KEY across runs (without requiring a `.env`).
  3. Picking a free loopback port and pointing the embedded webview at it.

Env vars are set BEFORE `from main import create_app` so the Flask config picks them
up. `main.load_env_file` uses setdefault/override=False, so any dev `.env` left in the
repo cannot clobber what we set here.
"""

from __future__ import annotations

import logging
import os
import secrets
import socket
import sys
import threading
from pathlib import Path
from typing import Tuple

from platformdirs import user_data_dir, user_log_dir

APP_NAME = "InventoryManagement"
APP_AUTHOR = "InventoryManagement"
WINDOW_TITLE = "Inventory Management"


def _resource_path(relative: str) -> Path:
    """Resolve a path that lives next to the source in dev or inside the PyInstaller bundle."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def _ensure_app_dirs() -> Tuple[Path, Path]:
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    log_dir = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    data_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, log_dir


def _load_or_create_secret(data_dir: Path) -> str:
    """Persist a strong session key in app-data so cookies survive restarts."""
    secret_path = data_dir / "secret_key"
    if secret_path.exists():
        existing = secret_path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    token = secrets.token_urlsafe(48)
    secret_path.write_text(token, encoding="utf-8")
    try:
        os.chmod(secret_path, 0o600)
    except OSError:
        pass
    return token


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _configure_env(data_dir: Path, log_dir: Path, port: int, secret: str) -> None:
    os.environ["INVENTORY_HOST"] = "127.0.0.1"
    os.environ["INVENTORY_PORT"] = str(port)
    os.environ["INVENTORY_DB_PATH"] = str(data_dir / "inventory.db")
    os.environ["INVENTORY_SECRET_KEY"] = secret
    # Desktop ships without baked-in admin credentials. ensure_seed_admin() treats
    # empty username/password as "skip" — first launch shows the register screen.
    os.environ["INVENTORY_ADMIN_USERNAME"] = ""
    os.environ["INVENTORY_ADMIN_PASSWORD"] = ""
    os.environ.setdefault(
        "INVENTORY_LOG_LEVEL",
        "DEBUG" if os.environ.get("INVENTORY_DEBUG") == "1" else "WARNING",
    )
    # Only set CORS origin if user hasn't overridden — desktop is same-origin anyway.
    os.environ.setdefault("INVENTORY_CORS_ORIGIN", f"http://127.0.0.1:{port}")
    bundled_frontend = _resource_path("inventory-management-web/dist")
    if bundled_frontend.is_dir() and (bundled_frontend / "index.html").exists():
        os.environ.setdefault("INVENTORY_FRONTEND_DIR", str(bundled_frontend))
    os.environ.setdefault("INVENTORY_LOG_DIR", str(log_dir))


def _configure_root_logging(log_dir: Path) -> None:
    """Route logs to a rotating file under app-data and stay quiet on stdout."""
    log_path = log_dir / "desktop.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if os.environ.get("INVENTORY_DEBUG") == "1" else logging.INFO)


def _serve_forever(app, port: int) -> None:
    from waitress import serve

    serve(
        app,
        host="127.0.0.1",
        port=port,
        threads=8,
        ident=APP_NAME,
        _quiet=True,
    )


def main() -> None:
    data_dir, log_dir = _ensure_app_dirs()
    _configure_root_logging(log_dir)
    secret = _load_or_create_secret(data_dir)
    port = _free_loopback_port()
    _configure_env(data_dir, log_dir, port, secret)

    # Import only after env is configured so create_app() reads our values.
    from main import create_app

    app = create_app()

    server = threading.Thread(
        target=_serve_forever,
        args=(app, port),
        name="waitress-server",
        daemon=True,
    )
    server.start()

    import webview

    webview.create_window(
        WINDOW_TITLE,
        f"http://127.0.0.1:{port}/",
        width=1280,
        height=820,
        min_size=(960, 640),
    )
    webview.start()


if __name__ == "__main__":
    main()