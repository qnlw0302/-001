from __future__ import annotations

import csv
import io
import json
import logging
import os
import secrets
import sqlite3
import time
from collections import deque
from datetime import timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, Optional, Tuple

from flask import (
    Flask,
    Response,
    current_app,
    g,
    jsonify,
    make_response,
    request,
    send_from_directory,
    session,
    stream_with_context,
)

from auth import (
    current_user,
    current_user_id,
    ensure_seed_admin,
    hash_password,
    login_required,
    login_user,
    logout_user,
    verify_current_password,
    verify_password,
)
from crud import (
    connect_db,
    init_audit_log_table,
    init_products_table,
    init_stock_movements_table,
    init_users_table,
)
from schemas import (
    ChangePasswordRequest,
    DeleteConfirmation,
    LoginRequest,
    MovementRequest,
    ProductCreate,
    ProductUpdate,
    RegisterRequest,
    UpdateProfileRequest,
)
from services import AccountLockedError, InventoryService


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_SRC_DIR = BASE_DIR / "inventory-management-web"
FRONTEND_DIST_DIR = FRONTEND_SRC_DIR / "dist"
DEFAULT_DB_PATH = BASE_DIR / "inventory.db"

CSRF_HEADER = "X-CSRF-Token"
CSRF_SESSION_KEY = "csrf_token"
CSRF_PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
CSRF_EXEMPT_PATHS = {"/api/auth/csrf"}


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def load_env_file(env_path: Path) -> None:
    """Load `.env` via python-dotenv if available, fall back to a minimal parser."""
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        return
    load_dotenv(dotenv_path=env_path, override=False)


load_env_file(BASE_DIR / ".env")


def _resolve_frontend_dir() -> Path:
    override = os.getenv("INVENTORY_FRONTEND_DIR")
    if override:
        return Path(override).resolve()
    if FRONTEND_DIST_DIR.is_dir() and (FRONTEND_DIST_DIR / "index.html").exists():
        return FRONTEND_DIST_DIR
    return FRONTEND_SRC_DIR


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(
        HOST=os.getenv("INVENTORY_HOST", "127.0.0.1"),
        PORT=int(os.getenv("INVENTORY_PORT", "5000")),
        DB_PATH=os.getenv("INVENTORY_DB_PATH", str(DEFAULT_DB_PATH)),
        SECRET_KEY=os.getenv("INVENTORY_SECRET_KEY", "dev-secret-change-me"),
        CORS_ORIGIN=os.getenv("INVENTORY_CORS_ORIGIN", "http://127.0.0.1:5173"),
        LOG_LEVEL=os.getenv("INVENTORY_LOG_LEVEL", "INFO"),
        ADMIN_USERNAME=os.getenv("INVENTORY_ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD=os.getenv("INVENTORY_ADMIN_PASSWORD", "change-me-admin-password"),
        FRONTEND_DIR=str(_resolve_frontend_dir()),
        JSON_SORT_KEYS=False,
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("INVENTORY_SESSION_SECURE", "0") == "1",
        SESSION_COOKIE_NAME="inventory_session",
        CSRF_ENABLED=os.getenv("INVENTORY_CSRF_ENABLED", "1") == "1",
        RATE_LIMIT_ENABLED=os.getenv("INVENTORY_RATE_LIMIT_ENABLED", "1") == "1",
        AUTH_RATE_LIMIT_MAX=int(os.getenv("INVENTORY_AUTH_RATE_LIMIT_MAX", "10")),
        AUTH_RATE_LIMIT_WINDOW=int(os.getenv("INVENTORY_AUTH_RATE_LIMIT_WINDOW", "60")),
        LOGIN_MAX_ATTEMPTS=int(os.getenv("INVENTORY_LOGIN_MAX_ATTEMPTS", "5")),
        LOGIN_LOCKOUT_SECONDS=int(os.getenv("INVENTORY_LOGIN_LOCKOUT_SECONDS", "900")),
    )
    if test_config:
        app.config.update(test_config)

    app.extensions["rate_limiter"] = RateLimiter()

    configure_logging(app)
    initialize_database(app)
    register_lifecycle_hooks(app)
    register_error_handlers(app)
    register_routes(app)
    return app


def configure_logging(app: Flask) -> None:
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    app.logger.setLevel(level)


def initialize_database(app: Flask) -> None:
    connection = connect_db(app.config["DB_PATH"])
    try:
        init_users_table(connection)
        init_audit_log_table(connection)
        with app.app_context():
            admin_id = ensure_seed_admin(
                connection,
                app.config["ADMIN_USERNAME"],
                app.config["ADMIN_PASSWORD"],
            )
        init_products_table(connection, default_owner_id=admin_id)
        init_stock_movements_table(connection)
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Rate limiting (in-memory sliding window)
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self) -> None:
        self._buckets: Dict[str, Deque[float]] = {}
        self._lock = Lock()

    def hit(self, key: str, max_hits: int, window_seconds: int) -> bool:
        """Return False when the caller has exceeded `max_hits` in `window_seconds`."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= max_hits:
                return False
            bucket.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)


def _rate_limit_or_reject(bucket: str) -> None:
    if not current_app.config.get("RATE_LIMIT_ENABLED", True):
        return
    limiter: RateLimiter = current_app.extensions["rate_limiter"]
    max_hits = int(current_app.config.get("AUTH_RATE_LIMIT_MAX", 10))
    window = int(current_app.config.get("AUTH_RATE_LIMIT_WINDOW", 60))
    key = f"{bucket}:{_client_ip()}"
    if not limiter.hit(key, max_hits, window):
        raise ApiError(
            "Too many requests. Try again in a moment.", 429
        )


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------
def _issue_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def _check_csrf() -> None:
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method not in CSRF_PROTECTED_METHODS:
        return
    if not request.path.startswith("/api/"):
        return
    if request.path in CSRF_EXEMPT_PATHS:
        return

    expected = session.get(CSRF_SESSION_KEY)
    provided = request.headers.get(CSRF_HEADER, "")
    if not expected or not provided or not secrets.compare_digest(str(expected), provided):
        raise ApiError("CSRF token missing or invalid.", 403)


# ---------------------------------------------------------------------------
# Lifecycle hooks + error handlers
# ---------------------------------------------------------------------------
def register_lifecycle_hooks(app: Flask) -> None:
    @app.before_request
    def before_request() -> Optional[Any]:
        if request.path.startswith("/api/"):
            current_app.logger.info("%s %s", request.method, request.full_path.rstrip("?"))

        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            return make_response("", 204)

        _check_csrf()
        return None

    @app.after_request
    def after_request(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'"
        )

        if request.path.startswith("/api/"):
            allowed_origin = current_app.config["CORS_ORIGIN"]
            request_origin = request.headers.get("Origin")
            if allowed_origin == "*":
                response.headers["Access-Control-Allow-Origin"] = "*"
            elif request_origin == allowed_origin:
                response.headers["Access-Control-Allow-Origin"] = allowed_origin
                response.headers["Vary"] = "Origin"
                response.headers["Access-Control-Allow-Credentials"] = "true"

            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = f"Content-Type, {CSRF_HEADER}"

        return response

    @app.teardown_appcontext
    def teardown_db(_error: Optional[BaseException]) -> None:
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(AccountLockedError)
    def handle_account_locked(error: AccountLockedError):
        response = jsonify({"error": str(error), "retry_after_seconds": error.retry_after_seconds})
        response.status_code = 429
        response.headers["Retry-After"] = str(error.retry_after_seconds)
        return response

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        status_code = 400 if is_api_request() else 500
        current_app.logger.warning("Value error: %s", error)
        return jsonify({"error": str(error)}), status_code

    @app.errorhandler(LookupError)
    def handle_lookup_error(error: LookupError):
        current_app.logger.info("Lookup error: %s", error)
        return jsonify({"error": str(error)}), 404

    @app.errorhandler(sqlite3.Error)
    def handle_sqlite_error(error: sqlite3.Error):
        current_app.logger.exception("Database error: %s", error)
        return jsonify({"error": "Database operation failed."}), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        current_app.logger.exception("Unexpected error: %s", error)
        return jsonify({"error": "Unexpected server error."}), 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
def register_routes(app: Flask) -> None:
    @app.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.route("/ready", methods=["GET"])
    def ready() -> Any:
        try:
            get_db().execute("SELECT 1").fetchone()
        except sqlite3.Error as error:
            current_app.logger.warning("Readiness check failed: %s", error)
            return jsonify({"status": "not_ready", "error": "database_unreachable"}), 503
        return jsonify({"status": "ready"})

    @app.route("/api/auth/csrf", methods=["GET"])
    def api_csrf() -> Any:
        token = _issue_csrf_token()
        return jsonify({"csrf_token": token})

    @app.route("/api/auth/register", methods=["POST"])
    def api_register() -> Any:
        _rate_limit_or_reject("auth:register")
        payload = read_json_body()
        data = RegisterRequest.from_payload(payload)
        service = get_service()
        if service.get_user_by_username(data.username) is not None:
            raise ApiError("Username already taken.", 409)
        user = service.create_user(data.username, hash_password(data.password))
        login_user(user.id, data.remember)
        service.record_login(user.id)
        _issue_csrf_token()
        return jsonify({"user": user.to_dict()}), 201

    @app.route("/api/auth/login", methods=["POST"])
    def api_login() -> Any:
        _rate_limit_or_reject("auth:login")
        payload = read_json_body()
        credentials = LoginRequest.from_payload(payload)
        service = get_service()

        lock = service.check_account_lock(credentials.username)
        if lock:
            raise AccountLockedError(retry_after_seconds=lock["retry_after_seconds"])

        record = service.get_user_by_username(credentials.username)
        if record is None or not verify_password(record["password_hash"], credentials.password):
            if record is not None:
                service.record_failed_login(record["id"])
            raise ApiError("Invalid username or password.", 401)

        service.reset_failed_logins(record["id"])
        login_user(record["id"], credentials.remember)
        service.record_login(record["id"])
        _issue_csrf_token()
        return jsonify({"user": {"id": record["id"], "username": record["username"]}})

    @app.route("/api/auth/logout", methods=["POST"])
    def api_logout() -> Any:
        user_id = current_user_id()
        if user_id is not None:
            try:
                get_service().record_logout(user_id)
            except sqlite3.Error:
                pass
        logout_user()
        return jsonify({"message": "Logged out."})

    @app.route("/api/auth/me", methods=["GET"])
    def api_me() -> Any:
        user = current_user(get_db())
        if user is None:
            return jsonify({"user": None}), 401
        return jsonify({"user": user.to_dict()})

    @app.route("/api/auth/bootstrap", methods=["GET"])
    def api_bootstrap() -> Any:
        """First-paint endpoint: tells the SPA whether to show login, register, or
        the inventory view. Combines the auth check with a user-existence probe so
        a fresh desktop install (no users yet) can land on the register screen
        instead of an empty login form."""
        user = current_user(get_db())
        has_users = get_service().count_users() > 0
        return jsonify({
            "user": user.to_dict() if user is not None else None,
            "has_users": has_users,
        })

    @app.route("/api/auth/me", methods=["PUT"])
    @login_required
    def api_update_me() -> Any:
        payload = read_json_body()
        data = UpdateProfileRequest.from_payload(payload)
        user_id = require_user_id()
        service = get_service()

        if not verify_current_password(get_db(), data.current_password):
            raise ApiError("Current password is incorrect.", 403)

        existing = service.get_user_by_username(data.username)
        if existing is not None and int(existing["id"]) != user_id:
            raise ApiError("Username already taken.", 409)

        if existing is not None and int(existing["id"]) == user_id:
            user = service.get_user_by_id(user_id)
        else:
            user = service.update_user_username(user_id, data.username)

        if user is None:
            raise LookupError("User not found.")
        return jsonify({"user": user.to_dict()})

    @app.route("/api/auth/change-password", methods=["POST"])
    @login_required
    def api_change_password() -> Any:
        payload = read_json_body()
        data = ChangePasswordRequest.from_payload(payload)
        user_id = require_user_id()
        service = get_service()

        if not verify_current_password(get_db(), data.current_password):
            raise ApiError("Current password is incorrect.", 403)

        service.update_user_password(user_id, hash_password(data.new_password))
        return jsonify({"message": "Password changed."})

    @app.route("/api/auth/audit", methods=["GET"])
    @login_required
    def api_audit_log() -> Any:
        user_id = require_user_id()
        limit = parse_positive_int(request.args.get("limit", "50"), "limit")
        events = get_service().list_audit_events(user_id, limit=limit)
        return jsonify({"items": events})

    @app.route("/api/products", methods=["GET"])
    @login_required
    def api_list_products() -> Any:
        search = request.args.get("search", "").strip()
        page = parse_positive_int(request.args.get("page", "1"), "page")
        limit = parse_positive_int(request.args.get("limit", "10"), "limit")
        payload = get_service().list_products(
            user_id=require_user_id(),
            search=search,
            page=page,
            limit=limit,
        )
        return jsonify(payload)

    @app.route("/api/products/export", methods=["GET"])
    @login_required
    def api_export_products() -> Any:
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt not in ("json", "csv"):
            raise ApiError("Format must be 'json' or 'csv'.", 400)
        user_id = require_user_id()
        if fmt == "json":
            items = [product.to_dict() for product in get_service().iter_all_products(user_id)]
            response = make_response(json.dumps({"items": items}, ensure_ascii=False))
            response.mimetype = "application/json"
            response.headers["Content-Disposition"] = "attachment; filename=products.json"
            return response

        @stream_with_context
        def csv_rows():
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow([
                "id",
                "sku",
                "name",
                "stock_qty",
                "status",
                "low_stock_threshold",
                "restock_threshold",
                "custom_fields",
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            for product in get_service().iter_all_products(user_id):
                writer.writerow([
                    product.id,
                    product.sku,
                    product.name,
                    product.stock_qty,
                    product.status,
                    "" if product.low_stock_threshold is None else product.low_stock_threshold,
                    product.effective_threshold,
                    json.dumps(product.custom_fields, ensure_ascii=False),
                ])
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

        response = Response(csv_rows(), mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=products.csv"
        return response

    @app.route("/api/products/<int:product_id>", methods=["GET"])
    @login_required
    def api_get_product(product_id: int) -> Any:
        product = get_service().get_product(require_user_id(), product_id)
        if product is None:
            raise LookupError("Product not found.")
        return jsonify(product.to_dict())

    @app.route("/api/products", methods=["POST"])
    @login_required
    def api_insert_product() -> Any:
        payload = read_json_body()
        product = get_service().insert_product(
            require_user_id(),
            ProductCreate.from_payload(payload),
        )
        return jsonify(product.to_dict()), 201

    @app.route("/api/products/<int:product_id>", methods=["PUT"])
    @login_required
    def api_update_product(product_id: int) -> Any:
        payload = read_json_body()
        product = get_service().update_product(
            require_user_id(),
            product_id,
            ProductUpdate.from_payload(payload),
        )
        return jsonify(product.to_dict())

    @app.route("/api/products/<int:product_id>", methods=["DELETE"])
    @login_required
    def api_delete_product(product_id: int) -> Any:
        payload = read_json_body()
        confirmation = DeleteConfirmation.from_payload(payload)
        if not verify_current_password(get_db(), confirmation.password):
            raise ApiError("Password does not match.", 403)
        deleted = get_service().delete_product(require_user_id(), product_id)
        if not deleted:
            raise LookupError("Product not found.")
        return jsonify({"message": "Product deleted."})

    @app.route("/api/products/<int:product_id>/movements", methods=["POST"])
    @login_required
    def api_record_movement(product_id: int) -> Any:
        payload = read_json_body()
        data = MovementRequest.from_payload(payload)
        movement, product = get_service().record_movement(
            require_user_id(),
            product_id,
            data,
        )
        return jsonify({"movement": movement.to_dict(), "product": product.to_dict()}), 201

    @app.route("/api/products/<int:product_id>/movements", methods=["GET"])
    @login_required
    def api_list_movements(product_id: int) -> Any:
        limit = parse_positive_int(request.args.get("limit", "50"), "limit")
        movements = get_service().list_movements(
            require_user_id(),
            product_id,
            limit=limit,
        )
        return jsonify({"items": [m.to_dict() for m in movements]})

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str) -> Any:
        if path.startswith("api/"):
            raise ApiError("Not found.", 404)

        frontend_root = Path(current_app.config["FRONTEND_DIR"]).resolve()
        requested_path = (frontend_root / path).resolve() if path else frontend_root / "index.html"
        try:
            requested_path.relative_to(frontend_root)
        except ValueError:
            raise ApiError("Forbidden.", 403)

        if requested_path.is_dir():
            requested_path = requested_path / "index.html"

        if requested_path.exists():
            relative_path = requested_path.relative_to(frontend_root)
            return send_from_directory(str(frontend_root), str(relative_path))
        return send_from_directory(str(frontend_root), "index.html")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_db(current_app.config["DB_PATH"])
    return g.db


def get_service() -> InventoryService:
    if "service" not in g:
        g.service = InventoryService(
            get_db(),
            request_ip=_client_ip() if request else None,
            max_login_attempts=int(current_app.config.get("LOGIN_MAX_ATTEMPTS", 5)),
            lockout_seconds=int(current_app.config.get("LOGIN_LOCKOUT_SECONDS", 900)),
        )
    return g.service


def require_user_id() -> int:
    user_id = current_user_id()
    if user_id is None:
        raise ApiError("Authentication required.", 401)
    return user_id


def parse_positive_int(raw_value: str, field_name: str) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ApiError("%s must be an integer." % field_name, 400)
    if value <= 0:
        raise ApiError("%s must be greater than 0." % field_name, 400)
    return value


def read_json_body() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    if payload is None:
        raise ApiError("Request body must be valid JSON.", 400)
    if not isinstance(payload, dict):
        raise ApiError("Request body must be a JSON object.", 400)
    return payload


def is_api_request() -> bool:
    return request.path.startswith("/api/")


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=False,
    )
