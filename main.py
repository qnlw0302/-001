from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from crud import delete_product, get_product, init_db, insert_product, list_all_products, update_product
from schemas import ProductCreate, ProductUpdate


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "inventory-management-web"
HOST = "127.0.0.1"
PORT = 5000


class InventoryHandler(BaseHTTPRequestHandler):
    server_version = "InventoryManagementHTTP/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/products":
            query = parse_qs(parsed.query)
            search = query.get("search", [""])[0].strip()
            products = [product.to_dict() for product in list_all_products(search)]
            self.send_json(200, products)
            return

        if path.startswith("/api/products/"):
            product_id = self.parse_product_id(path)
            if product_id is None:
                self.send_json(404, {"error": "Product not found."})
                return

            product = get_product(product_id)
            if product is None:
                self.send_json(404, {"error": "Product not found."})
                return

            self.send_json(200, product.to_dict())
            return

        if path == "/health":
            self.send_json(200, {"status": "ok"})
            return

        self.serve_frontend(path)

    def do_POST(self) -> None:
        if self.path != "/api/products":
            self.send_json(404, {"error": "Not found."})
            return

        try:
            payload = self.read_json_body()
            product = insert_product(ProductCreate.from_payload(payload))
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Request body must be valid JSON."})
            return

        self.send_json(201, product.to_dict())

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        product_id = self.parse_product_id(parsed.path)
        if product_id is None:
            self.send_json(404, {"error": "Product not found."})
            return

        try:
            payload = self.read_json_body()
            product = update_product(product_id, ProductUpdate.from_payload(payload))
        except LookupError as error:
            self.send_json(404, {"error": str(error)})
            return
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Request body must be valid JSON."})
            return

        self.send_json(200, product.to_dict())

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        product_id = self.parse_product_id(parsed.path)
        if product_id is None:
            self.send_json(404, {"error": "Product not found."})
            return

        deleted = delete_product(product_id)
        if not deleted:
            self.send_json(404, {"error": "Product not found."})
            return

        self.send_json(200, {"message": "Product deleted."})

    def serve_frontend(self, request_path: str) -> None:
        relative_path = request_path.lstrip("/") or "index.html"
        safe_path = (FRONTEND_DIR / unquote(relative_path)).resolve()
        frontend_root = FRONTEND_DIR.resolve()

        try:
            safe_path.relative_to(frontend_root)
        except ValueError:
            self.send_json(403, {"error": "Forbidden."})
            return

        if safe_path.is_dir():
            safe_path = safe_path / "index.html"

        if not safe_path.exists():
            safe_path = frontend_root / "index.html"

        if not safe_path.exists():
            self.send_json(500, {"error": "Frontend files are missing."})
            return

        content_type, _ = mimetypes.guess_type(str(safe_path))
        if content_type is None:
            content_type = "application/octet-stream"

        body = safe_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        payload = json.loads(raw_body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def parse_product_id(self, path: str) -> int | None:
        parts = [part for part in path.split("/") if part]
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "products":
            return None
        try:
            return int(parts[2])
        except ValueError:
            return None

    def send_json(self, status: int, payload: dict[str, object] | list[dict[str, object]]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def run() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), InventoryHandler)
    print(f"Inventory backend running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
