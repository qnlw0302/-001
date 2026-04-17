from __future__ import annotations

import logging
import os
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, current_app, g, jsonify, make_response, request, send_from_directory

from auth import (
    current_user,
    ensure_seed_admin,
    login_required,
    login_user,
    logout_user,
    verify_current_password,
    verify_password,
)
from crud import (
    connect_db,
    delete_product,
    get_product,
    get_user_by_username,
    init_db,
    insert_product,
    list_products,
    update_product,
)
from schemas import DeleteConfirmation, LoginRequest, ProductCreate, ProductUpdate


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "inventory-management-web"
DEFAULT_DB_PATH = BASE_DIR / "inventory.db"


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(BASE_DIR / ".env")


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
        ADMIN_PASSWORD=os.getenv("INVENTORY_ADMIN_PASSWORD", "admin123"),
        FRONTEND_DIR=str(FRONTEND_DIR),
        JSON_SORT_KEYS=False,
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("INVENTORY_SESSION_SECURE", "0") == "1",
        SESSION_COOKIE_NAME="inventory_session",
    )
    if test_config:
        app.config.update(test_config)

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
        init_db(connection)
        with app.app_context():
            ensure_seed_admin(
                connection,
                app.config["ADMIN_USERNAME"],
                app.config["ADMIN_PASSWORD"],
            )
    finally:
        connection.close()


def register_lifecycle_hooks(app: Flask) -> None:
    @app.before_request
    def before_request() -> Optional[Any]:
        if request.path.startswith("/api/"):
            current_app.logger.info("%s %s", request.method, request.full_path.rstrip("?"))

        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            return make_response("", 204)
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
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"

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


def register_routes(app: Flask) -> None:
    @app.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.route("/api/auth/login", methods=["POST"])
    def api_login() -> Any:
        payload = read_json_body()
        credentials = LoginRequest.from_payload(payload)
        record = get_user_by_username(get_db(), credentials.username)
        if record is None or not verify_password(record["password_hash"], credentials.password):
            raise ApiError("Invalid username or password.", 401)
        login_user(record["id"], credentials.remember)
        return jsonify({"user": {"id": record["id"], "username": record["username"]}})

    @app.route("/api/auth/logout", methods=["POST"])
    def api_logout() -> Any:
        logout_user()
        return jsonify({"message": "Logged out."})

    @app.route("/api/auth/me", methods=["GET"])
    def api_me() -> Any:
        user = current_user(get_db())
        if user is None:
            return jsonify({"user": None}), 401
        return jsonify({"user": user.to_dict()})

    @app.route("/api/products", methods=["GET"])
    def api_list_products() -> Any:
        search = request.args.get("search", "").strip()
        page = parse_positive_int(request.args.get("page", "1"), "page")
        limit = parse_positive_int(request.args.get("limit", "10"), "limit")
        payload = list_products(get_db(), search=search, page=page, limit=limit)
        return jsonify(payload)

    @app.route("/api/products/<int:product_id>", methods=["GET"])
    def api_get_product(product_id: int) -> Any:
        product = get_product(get_db(), product_id)
        if product is None:
            raise LookupError("Product not found.")
        return jsonify(product.to_dict())

    @app.route("/api/products", methods=["POST"])
    @login_required
    def api_insert_product() -> Any:
        payload = read_json_body()
        product = insert_product(get_db(), ProductCreate.from_payload(payload))
        return jsonify(product.to_dict()), 201

    @app.route("/api/products/<int:product_id>", methods=["PUT"])
    @login_required
    def api_update_product(product_id: int) -> Any:
        payload = read_json_body()
        product = update_product(get_db(), product_id, ProductUpdate.from_payload(payload))
        return jsonify(product.to_dict())

    @app.route("/api/products/<int:product_id>", methods=["DELETE"])
    @login_required
    def api_delete_product(product_id: int) -> Any:
        payload = read_json_body()
        confirmation = DeleteConfirmation.from_payload(payload)
        if not verify_current_password(get_db(), confirmation.password):
            raise ApiError("Password does not match.", 403)
        deleted = delete_product(get_db(), product_id)
        if not deleted:
            raise LookupError("Product not found.")
        return jsonify({"message": "Product deleted."})

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
