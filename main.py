"""
产品列表，可以看得到当前库存，阈值和状态（正常、低库存、缺货）。可以添加新产品，编辑现有产品的库存和阈值，以及删除产品。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict

from flask import Flask, request, jsonify, g, render_template_string

app = Flask(__name__)

DB_PATH = "inventory.db"


# -----------------------
# Product Schema (simple)
# -----------------------
@dataclass
class Product:
    sku: str
    name: str
    stock_qty: int = 0
    low_stock_threshold: int = 10

    @staticmethod
    def validate_payload(payload: Dict[str, Any], partial: bool = False) -> "Product | Dict[str, Any]":
        """
        partial=False: 创建用，字段必须齐全(sku, name)
        partial=True: 更新用，字段可缺省
        返回 Product 或 {"error": "..."}。
        """
        def err(msg: str):
            return {"error": msg}

        sku = payload.get("sku")
        name = payload.get("name")
        stock_qty = payload.get("stock_qty")
        low_stock_threshold = payload.get("low_stock_threshold")

        if not partial:
            if not isinstance(sku, str) or not sku.strip():
                return err("sku is required and must be a non-empty string")
            if not isinstance(name, str) or not name.strip():
                return err("name is required and must be a non-empty string")
        else:
            if sku is not None and (not isinstance(sku, str) or not sku.strip()):
                return err("sku must be a non-empty string")
            if name is not None and (not isinstance(name, str) or not name.strip()):
                return err("name must be a non-empty string")

        if stock_qty is None:
            stock_qty = 0
        if low_stock_threshold is None:
            low_stock_threshold = 10

        if stock_qty is not None:
            try:
                stock_qty = int(stock_qty)
            except Exception:
                return err("stock_qty must be an integer")
            if stock_qty < 0:
                return err("stock_qty must be >= 0")

        if low_stock_threshold is not None:
            try:
                low_stock_threshold = int(low_stock_threshold)
            except Exception:
                return err("low_stock_threshold must be an integer")
            if low_stock_threshold < 0:
                return err("low_stock_threshold must be >= 0")

        # partial 更新时，sku/name 可能是 None，这里先给占位，实际 update 时按提供字段更新
        return Product(
            sku=(sku.strip() if isinstance(sku, str) else ""),
            name=(name.strip() if isinstance(name, str) else ""),
            stock_qty=stock_qty,
            low_stock_threshold=low_stock_threshold,
        )


# -----------------------
# DB helpers
# -----------------------
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            stock_qty INTEGER NOT NULL DEFAULT 0,
            low_stock_threshold INTEGER NOT NULL DEFAULT 10
        );
        """
    )
    db.commit()
    db.close()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "sku": row["sku"],
        "name": row["name"],
        "stock_qty": row["stock_qty"],
        "low_stock_threshold": row["low_stock_threshold"],
        "status": status_label(row["stock_qty"], row["low_stock_threshold"]),
    }


def status_label(stock_qty: int, threshold: int) -> str:
    if stock_qty == 0:
        return "out"   # 缺货
    if stock_qty <= threshold:
        return "low"   # 低库存
    return "ok"        # 正常


# -----------------------
# CRUD APIs
# -----------------------

# Insert product
@app.route("/api/products", methods=["POST"])
def create_product():
    payload = request.get_json(silent=True) or {}
    validated = Product.validate_payload(payload, partial=False)
    if isinstance(validated, dict) and "error" in validated:
        return jsonify(validated), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO products (sku, name, stock_qty, low_stock_threshold) VALUES (?, ?, ?, ?)",
            (validated.sku, validated.name, validated.stock_qty, validated.low_stock_threshold),
        )
        db.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "sku already exists"}), 400

    row = db.execute("SELECT * FROM products WHERE id = ?", (new_id,)).fetchone()
    return jsonify(row_to_dict(row)), 201


# List all product
@app.route("/api/products", methods=["GET"])
def list_products():
    # 可选筛选: ?status=low|out|ok  ,  ?search=xxx(匹配 sku 或 name)
    status = request.args.get("status")
    search = request.args.get("search")

    db = get_db()
    rows = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    items = [row_to_dict(r) for r in rows]

    if search:
        s = search.strip().lower()
        items = [p for p in items if s in p["sku"].lower() or s in p["name"].lower()]

    if status in ("low", "out", "ok"):
        items = [p for p in items if p["status"] == status]

    return jsonify(items)


# Get product
@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        return jsonify({"error": "product not found"}), 404
    return jsonify(row_to_dict(row))


# Update product (partial update)
@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id: int):
    payload = request.get_json(silent=True) or {}
    validated = Product.validate_payload(payload, partial=True)
    if isinstance(validated, dict) and "error" in validated:
        return jsonify(validated), 400

    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        return jsonify({"error": "product not found"}), 404

    new_sku = payload.get("sku", row["sku"])
    new_name = payload.get("name", row["name"])
    new_stock_qty = payload.get("stock_qty", row["stock_qty"])
    new_low = payload.get("low_stock_threshold", row["low_stock_threshold"])

    # 统一转型和校验
    check = Product.validate_payload(
        {"sku": new_sku, "name": new_name, "stock_qty": new_stock_qty, "low_stock_threshold": new_low},
        partial=False,
    )
    if isinstance(check, dict) and "error" in check:
        return jsonify(check), 400

    try:
        db.execute(
            "UPDATE products SET sku=?, name=?, stock_qty=?, low_stock_threshold=? WHERE id=?",
            (check.sku, check.name, check.stock_qty, check.low_stock_threshold, product_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "sku already exists"}), 400

    row2 = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify(row_to_dict(row2))


# Delete product
@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        return jsonify({"error": "product not found"}), 404

    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return ("", 204)

LOW_STOCK_PAGE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Low Stock</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body{font-family:Arial, sans-serif; margin:20px; max-width:1100px;}
    table{border-collapse:collapse; width:100%;}
    th,td{border:1px solid #ddd; padding:10px; text-align:left;}
    .tag{padding:2px 10px; border-radius:999px; display:inline-block; font-size:12px;}
    .ok{background:#e6ffed;}
    .low{background:#fff5cc;}
    .out{background:#ffe6e6;}
    .row{display:flex; gap:10px; flex-wrap:wrap; align-items:center;}
    input, select{padding:8px; border:1px solid #ccc; border-radius:8px;}
    button{padding:8px 12px; border:1px solid #333; background:#fff; border-radius:10px; cursor:pointer;}
    button:hover{background:#f3f3f3;}
    .muted{color:#666;}
    .card{border:1px solid #ddd; border-radius:12px; padding:14px; min-width:220px;}
  </style>
</head>
<body>
  <h2>库存看板</h2>

  <div class="row">
    <div class="card">
      <div class="muted">总产品数</div>
      <div style="font-size:28px; margin-top:8px;">{{ total }}</div>
    </div>
    <div class="card">
      <div class="muted">低库存</div>
      <div style="font-size:28px; margin-top:8px;">{{ low_count }}</div>
    </div>
    <div class="card">
      <div class="muted">缺货</div>
      <div style="font-size:28px; margin-top:8px;">{{ out_count }}</div>
    </div>
  </div>

  <hr>

  <form class="row" method="get" action="/">
    <input name="search" value="{{ search }}" placeholder="搜索 SKU 或名称">
    <select name="view">
      <option value="low" {% if view=="low" %}selected{% endif %}>低库存</option>
      <option value="out" {% if view=="out" %}selected{% endif %}>缺货</option>
      <option value="all" {% if view=="all" %}selected{% endif %}>全部</option>
    </select>
    <button type="submit">筛选</button>
    <a class="muted" href="/">清除</a>
  </form>

  <p class="muted">当前显示 {{ items|length }} 条。</p>

  <table>
    <tr>
      <th>ID</th>
      <th>SKU</th>
      <th>名称</th>
      <th>库存</th>
      <th>阈值</th>
      <th>状态</th>
    </tr>
    {% for p in items %}
    <tr>
      <td>{{ p.id }}</td>
      <td>{{ p.sku }}</td>
      <td>{{ p.name }}</td>
      <td>{{ p.stock_qty }}</td>
      <td>{{ p.low_stock_threshold }}</td>
      <td>
        {% if p.status == "ok" %}<span class="tag ok">正常</span>{% endif %}
        {% if p.status == "low" %}<span class="tag low">低库存</span>{% endif %}
        {% if p.status == "out" %}<span class="tag out">缺货</span>{% endif %}
      </td>
    </tr>
    {% endfor %}
  </table>

  <p class="muted" style="margin-top:16px;">
    API: <code>/api/products</code>
  </p>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def low_stock_page():
    view = request.args.get("view", "low")   # low / out / all
    search = (request.args.get("search") or "").strip()

    db = get_db()
    rows = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    items = [row_to_dict(r) for r in rows]

    low = [p for p in items if p["status"] == "low"]
    out = [p for p in items if p["status"] == "out"]

    # 搜索过滤
    if search:
        s = search.lower()
        items = [p for p in items if s in p["sku"].lower() or s in p["name"].lower()]
        low = [p for p in low if s in p["sku"].lower() or s in p["name"].lower()]
        out = [p for p in out if s in p["sku"].lower() or s in p["name"].lower()]

    # 视图选择
    if view == "out":
        show = out
    elif view == "all":
        show = items
    else:
        show = low

    return render_template_string(
        LOW_STOCK_PAGE_HTML,
        total=len(rows),
        low_count=len(low),
        out_count=len(out),
        items=show,
        view=view,
        search=search,
    )

# -----------------------
# Start server
# -----------------------
if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)