import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.environ.get("ROTASABOR_DATA_FILE", str(BASE_DIR / "rotasabor_db.json")))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# O Render costuma fornecer postgres://; bibliotecas modernas preferem postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://") :]

USE_POSTGRES = bool(DATABASE_URL)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "static"),
    template_folder=str(BASE_DIR / "templates"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_last4(phone_raw: Any) -> str:
    digits = re.sub(r"\D", "", str(phone_raw or ""))
    return digits[-4:] if len(digits) >= 4 else "1234"


def _default_data() -> dict[str, list[dict[str, Any]]]:
    return {
        "clients": [],
        "stores": [
            {
                "id": 1,
                "name": "Hamburgueria Centro",
                "category": "Lanches & Pizzas",
                "city": "Catanduva - SP",
                "delivery_fee": 8.0,
                "prep_time": "25-35 min",
                "active": True,
                "created_at": _now_iso(),
            },
            {
                "id": 2,
                "name": "Marmitaria Sabor da Casa",
                "category": "Refeições & Marmitas",
                "city": "Catanduva - SP",
                "delivery_fee": 7.0,
                "prep_time": "30-45 min",
                "active": True,
                "created_at": _now_iso(),
            },
        ],
        "couriers": [],
        "orders": [],
    }


def _pg_connect():
    if psycopg is None:
        raise RuntimeError(
            "DATABASE_URL configurada, mas o pacote 'psycopg' não está instalado. "
            "Adicione 'psycopg[binary]' ao requirements.txt."
        )
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _init_db() -> None:
    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clients (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        phone TEXT NOT NULL DEFAULT '',
                        address TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS stores (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL DEFAULT 'Geral',
                        city TEXT NOT NULL DEFAULT 'Catanduva - SP',
                        delivery_fee DOUBLE PRECISION NOT NULL DEFAULT 0,
                        prep_time TEXT NOT NULL DEFAULT '30 min',
                        active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS couriers (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        phone TEXT NOT NULL DEFAULT '',
                        vehicle TEXT NOT NULL DEFAULT 'Moto',
                        plate TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'offline',
                        lat DOUBLE PRECISION,
                        lng DOUBLE PRECISION,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS orders (
                        id SERIAL PRIMARY KEY,
                        order_code TEXT NOT NULL DEFAULT '',
                        client_id INTEGER,
                        client_name TEXT NOT NULL DEFAULT 'Cliente Balcão',
                        customer_phone TEXT NOT NULL DEFAULT '',
                        customer_phone_last4 TEXT NOT NULL DEFAULT '1234',
                        client_address TEXT NOT NULL DEFAULT '',
                        store_id INTEGER,
                        store_name TEXT NOT NULL DEFAULT '',
                        courier_id INTEGER,
                        items_json TEXT NOT NULL DEFAULT '[]',
                        delivery_fee DOUBLE PRECISION NOT NULL DEFAULT 0,
                        total DOUBLE PRECISION NOT NULL DEFAULT 0,
                        payment TEXT NOT NULL DEFAULT 'Pix',
                        status TEXT NOT NULL DEFAULT 'Pendente',
                        store_ready BOOLEAN NOT NULL DEFAULT FALSE,
                        courier_accepted BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_code TEXT NOT NULL DEFAULT '';
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_phone TEXT NOT NULL DEFAULT '';
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_phone_last4 TEXT NOT NULL DEFAULT '1234';
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_fee DOUBLE PRECISION NOT NULL DEFAULT 0;
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS store_ready BOOLEAN NOT NULL DEFAULT FALSE;
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS courier_accepted BOOLEAN NOT NULL DEFAULT FALSE;
                    """
                )
                cur.execute("SELECT COUNT(*) AS cnt FROM stores;")
                row = cur.fetchone()
                if row and row["cnt"] == 0:
                    for s in _default_data()["stores"]:
                        cur.execute(
                            """
                            INSERT INTO stores (name, category, city, delivery_fee, prep_time, active, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                s["name"],
                                s["category"],
                                s["city"],
                                s["delivery_fee"],
                                s["prep_time"],
                                s["active"],
                                s["created_at"],
                            ),
                        )
            conn.commit()
    else:
        if not DATA_FILE.exists():
            _write_json_db(_default_data())


def _read_json_db() -> dict[str, list[dict[str, Any]]]:
    if not DATA_FILE.exists():
        data = _default_data()
        _write_json_db(data)
        return data
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return _default_data()
        base = _default_data()
        for k in base:
            if isinstance(raw.get(k), list):
                base[k] = raw[k]
        return base
    except Exception:
        return _default_data()


def _write_json_db(data: dict[str, list[dict[str, Any]]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _format_order_row(row: dict[str, Any]) -> dict[str, Any]:
    items_raw = row.get("items_json")
    if isinstance(items_raw, str):
        try:
            items = json.loads(items_raw)
        except Exception:
            items = []
    elif isinstance(items_raw, list):
        items = items_raw
    else:
        items = row.get("items") or []

    oid = row.get("id")
    default_code = f"RS-{int(oid):03d}" if oid is not None else "RS-000"
    code = str(row.get("order_code") or "").strip() or default_code

    return {
        "id": oid,
        "order_code": code,
        "client_id": row.get("client_id"),
        "client_name": row.get("client_name") or "Cliente",
        "customer_phone": row.get("customer_phone") or "",
        "customer_phone_last4": str(row.get("customer_phone_last4") or "1234"),
        "client_address": row.get("client_address") or "",
        "store_id": row.get("store_id"),
        "store_name": row.get("store_name") or "",
        "courier_id": row.get("courier_id"),
        "items": items,
        "delivery_fee": float(row.get("delivery_fee") or 0),
        "total": float(row.get("total") or 0),
        "payment": row.get("payment") or "Pix",
        "status": row.get("status") or "Pendente",
        "store_ready": bool(row.get("store_ready", False)),
        "courier_accepted": bool(row.get("courier_accepted", False)),
        "created_at": row.get("created_at") or "",
        "updated_at": row.get("updated_at") or "",
    }


try:
    _init_db()
except Exception as exc:
    app.logger.warning("Aviso na inicialização do banco: %s", exc)


# --- Rotas de Páginas ---


@app.route("/")
def index():
    return render_template("painel_gestao.html")


@app.route("/painel")
def painel():
    return render_template("painel_gestao.html")


@app.route("/app-cliente")
def app_cliente():
    return render_template("app_cliente.html")


@app.route("/app-motoboy")
def app_motoboy():
    return render_template("app_motoboy.html")


@app.route("/loja")
def loja():
    return render_template("loja.html")


@app.route("/manifest.json")
def manifest_json():
    return send_from_directory(app.static_folder, "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker_js():
    response = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


# --- API: Clientes ---


@app.route("/api/clients", methods=["GET", "POST"])
def clients_collection():
    if request.method == "GET":
        if USE_POSTGRES:
            with _pg_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM clients ORDER BY id DESC;")
                    return jsonify([dict(r) for r in cur.fetchall()]), 200
        db = _read_json_db()
        return jsonify(list(reversed(db["clients"]))), 200

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    phone = str(payload.get("phone") or "").strip()
    address = str(payload.get("address") or "").strip()
    if not name:
        return jsonify({"error": "Nome do cliente é obrigatório"}), 400

    now = _now_iso()
    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO clients (name, phone, address, created_at)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (name, phone, address, now),
                )
                created = dict(cur.fetchone())
            conn.commit()
        return jsonify(created), 201

    db = _read_json_db()
    next_id = max([int(c.get("id", 0)) for c in db["clients"]], default=0) + 1
    client = {
        "id": next_id,
        "name": name,
        "phone": phone,
        "address": address,
        "created_at": now,
    }
    db["clients"].append(client)
    _write_json_db(db)
    return jsonify(client), 201


# --- API: Estabelecimentos ---


@app.route("/api/stores", methods=["GET", "POST"])
def stores_collection():
    if request.method == "GET":
        if USE_POSTGRES:
            with _pg_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM stores ORDER BY id ASC;")
                    return jsonify([dict(r) for r in cur.fetchall()]), 200
        db = _read_json_db()
        return jsonify(db["stores"]), 200

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nome do estabelecimento é obrigatório"}), 400

    category = str(payload.get("category") or "Geral").strip()
    city = str(payload.get("city") or "Catanduva - SP").strip()
    delivery_fee = float(payload.get("delivery_fee") or 0)
    prep_time = str(payload.get("prep_time") or "30-40 min").strip()
    active = bool(payload.get("active", True))
    now = _now_iso()

    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stores (name, category, city, delivery_fee, prep_time, active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (name, category, city, delivery_fee, prep_time, active, now),
                )
                created = dict(cur.fetchone())
            conn.commit()
        return jsonify(created), 201

    db = _read_json_db()
    next_id = max([int(s.get("id", 0)) for s in db["stores"]], default=0) + 1
    store = {
        "id": next_id,
        "name": name,
        "category": category,
        "city": city,
        "delivery_fee": delivery_fee,
        "prep_time": prep_time,
        "active": active,
        "created_at": now,
    }
    db["stores"].append(store)
    _write_json_db(db)
    return jsonify(store), 201


# --- API: Entregadores ---


@app.route("/api/couriers", methods=["GET", "POST"])
def couriers_collection():
    if request.method == "GET":
        if USE_POSTGRES:
            with _pg_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM couriers ORDER BY id DESC;")
                    return jsonify([dict(r) for r in cur.fetchall()]), 200
        db = _read_json_db()
        return jsonify(list(reversed(db["couriers"]))), 200

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nome do entregador é obrigatório"}), 400

    phone = str(payload.get("phone") or "").strip()
    vehicle = str(payload.get("vehicle") or "Moto").strip()
    plate = str(payload.get("plate") or "").strip().upper()
    status = str(payload.get("status") or "online").strip()
    now = _now_iso()

    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO couriers (name, phone, vehicle, plate, status, lat, lng, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s)
                    RETURNING *;
                    """,
                    (name, phone, vehicle, plate, status, now),
                )
                created = dict(cur.fetchone())
            conn.commit()
        return jsonify(created), 201

    db = _read_json_db()
    next_id = max([int(c.get("id", 0)) for c in db["couriers"]], default=0) + 1
    courier = {
        "id": next_id,
        "name": name,
        "phone": phone,
        "vehicle": vehicle,
        "plate": plate,
        "status": status,
        "lat": None,
        "lng": None,
        "updated_at": now,
    }
    db["couriers"].append(courier)
    _write_json_db(db)
    return jsonify(courier), 201


@app.route("/api/couriers/<int:courier_id>/location", methods=["POST"])
def update_courier_location(courier_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        lat = float(payload["lat"])
        lng = float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Latitude e longitude válidas são obrigatórias"}), 400

    now = _now_iso()
    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE couriers
                    SET lat = %s, lng = %s, updated_at = %s
                    WHERE id = %s
                    RETURNING *;
                    """,
                    (lat, lng, now, courier_id),
                )
                updated = cur.fetchone()
            conn.commit()
        if not updated:
            return jsonify({"error": "Entregador não encontrado"}), 404
        return jsonify(dict(updated)), 200

    db = _read_json_db()
    for c in db["couriers"]:
        if int(c.get("id", 0)) == courier_id:
            c["lat"] = lat
            c["lng"] = lng
            c["updated_at"] = now
            _write_json_db(db)
            return jsonify(c), 200
    return jsonify({"error": "Entregador não encontrado"}), 404


# --- API: Pedidos / Entregas ---


@app.route("/api/orders", methods=["GET", "POST"])
def orders_collection():
    if request.method == "GET":
        if USE_POSTGRES:
            with _pg_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM orders ORDER BY id ASC;")
                    return jsonify([_format_order_row(dict(r)) for r in cur.fetchall()]), 200
        db = _read_json_db()
        return jsonify([_format_order_row(o) for o in db["orders"]]), 200

    payload = request.get_json(silent=True) or {}
    items = payload.get("items") or []
    if not items:
        return jsonify({"error": "Carrinho vazio"}), 400

    now = _now_iso()
    client_id = payload.get("client_id")
    client_name = str(payload.get("client_name") or "Cliente").strip()
    customer_phone = str(payload.get("customer_phone") or payload.get("phone") or "").strip()
    last4_raw = str(payload.get("customer_phone_last4") or "").strip()
    last4 = last4_raw if (len(last4_raw) == 4 and last4_raw.isdigit()) else _extract_last4(customer_phone)
    client_address = str(payload.get("client_address") or "").strip()
    store_id = payload.get("store_id")
    store_name = str(payload.get("store_name") or "").strip()
    delivery_fee = float(payload.get("delivery_fee") or 0)
    total = float(payload.get("total") or 0)
    payment = str(payload.get("payment") or "Pix").strip()
    store_ready = bool(payload.get("store_ready", False))
    courier_accepted = bool(payload.get("courier_accepted", False))
    status_val = str(payload.get("status") or "Pendente").strip()

    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (
                        order_code, client_id, client_name, customer_phone, customer_phone_last4,
                        client_address, store_id, store_name, courier_id,
                        items_json, delivery_fee, total, payment, status,
                        store_ready, courier_accepted, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (
                        "",
                        client_id,
                        client_name,
                        customer_phone,
                        last4,
                        client_address,
                        store_id,
                        store_name,
                        json.dumps(items, ensure_ascii=False),
                        delivery_fee,
                        total,
                        payment,
                        status_val,
                        store_ready,
                        courier_accepted,
                        now,
                        now,
                    ),
                )
                row = dict(cur.fetchone())
                oid = int(row["id"])
                code = str(payload.get("order_code") or "").strip() or f"RS-{oid:03d}"
                cur.execute(
                    "UPDATE orders SET order_code = %s WHERE id = %s RETURNING *;",
                    (code, oid),
                )
                created = _format_order_row(dict(cur.fetchone()))
            conn.commit()
        return jsonify(created), 201

    db = _read_json_db()
    next_id = max([int(o.get("id", 0)) for o in db["orders"]], default=0) + 1
    code = str(payload.get("order_code") or "").strip() or f"RS-{next_id:03d}"
    new_order = {
        "id": next_id,
        "order_code": code,
        "client_id": client_id,
        "client_name": client_name,
        "customer_phone": customer_phone,
        "customer_phone_last4": last4,
        "client_address": client_address,
        "store_id": store_id,
        "store_name": store_name,
        "courier_id": None,
        "items_json": json.dumps(items, ensure_ascii=False),
        "delivery_fee": delivery_fee,
        "total": total,
        "payment": payment,
        "status": status_val,
        "store_ready": store_ready,
        "courier_accepted": courier_accepted,
        "created_at": now,
        "updated_at": now,
    }
    db["orders"].append(new_order)
    _write_json_db(db)
    return jsonify(_format_order_row(new_order)), 201


@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
def update_order(order_id: int):
    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status")
    courier_id = payload.get("courier_id")
    now = _now_iso()

    def _validate_and_apply(current: dict[str, Any]) -> tuple[dict[str, Any] | None, tuple[str, int] | None]:
        if new_status is not None and str(new_status).strip().lower() == "entregue":
            expected_code = str(current.get("customer_phone_last4") or "").strip()
            provided_code = str(payload.get("delivery_code") or payload.get("last4") or "").strip()
            if expected_code and provided_code != expected_code:
                return None, ("Código de confirmação (4 últimos dígitos) inválido.", 400)

        updated = dict(current)
        if new_status is not None and str(new_status).strip():
            updated["status"] = str(new_status).strip()
        if courier_id is not None:
            updated["courier_id"] = courier_id
        if "store_ready" in payload:
            updated["store_ready"] = bool(payload["store_ready"])
        if "courier_accepted" in payload:
            updated["courier_accepted"] = bool(payload["courier_accepted"])
        if "delivery_fee" in payload and payload["delivery_fee"] is not None:
            updated["delivery_fee"] = float(payload["delivery_fee"])
        updated["updated_at"] = now
        return updated, None

    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM orders WHERE id = %s;", (order_id,))
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Pedido não encontrado"}), 404

                updated, err = _validate_and_apply(dict(row))
                if err:
                    msg, code = err
                    return jsonify({"error": msg}), code

                cur.execute(
                    """
                    UPDATE orders
                    SET status = %s,
                        courier_id = %s,
                        store_ready = %s,
                        courier_accepted = %s,
                        delivery_fee = %s,
                        updated_at = %s
                    WHERE id = %s
                    RETURNING *;
                    """,
                    (
                        updated["status"],
                        updated["courier_id"],
                        updated["store_ready"],
                        updated["courier_accepted"],
                        updated["delivery_fee"],
                        updated["updated_at"],
                        order_id,
                    ),
                )
                formatted = _format_order_row(dict(cur.fetchone()))
            conn.commit()
        return jsonify(formatted), 200

    db = _read_json_db()
    for idx, o in enumerate(db["orders"]):
        if int(o.get("id", 0)) == order_id:
            updated, err = _validate_and_apply(o)
            if err:
                msg, code = err
                return jsonify({"error": msg}), code
            db["orders"][idx] = updated
            _write_json_db(db)
            return jsonify(_format_order_row(updated)), 200

    return jsonify({"error": "Pedido não encontrado"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
