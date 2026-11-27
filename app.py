import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.environ.get("ROTASABOR_DATA_FILE", str(BASE_DIR / "rotasabor_db.json")))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

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


def _default_data() -> dict[str, list[dict[str, Any]]]:
    return {
        "clients": [],
        "stores": [
            {
                "id": 1,
                "name": "Hamburgueria Centro",
                "category": "Lanches & Smash",
                "city": "Catanduva - SP",
                "delivery_fee": 8.0,
                "prep_time": "25-35 min",
                "active": True,
                "created_at": _now_iso(),
            },
            {
                "id": 2,
                "name": "Marmitaria Sabor da Casa",
                "category": "Refeicoes Caseiras",
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
                        client_id INTEGER,
                        client_name TEXT NOT NULL DEFAULT 'Cliente Balcão',
                        client_address TEXT NOT NULL DEFAULT '',
                        store_id INTEGER,
                        store_name TEXT NOT NULL DEFAULT '',
                        courier_id INTEGER,
                        items_json TEXT NOT NULL DEFAULT '[]',
                        total DOUBLE PRECISION NOT NULL DEFAULT 0,
                        payment TEXT NOT NULL DEFAULT 'Pix',
                        status TEXT NOT NULL DEFAULT 'Pendente',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
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
        items = []
    return {
        "id": row.get("id"),
        "client_id": row.get("client_id"),
        "client_name": row.get("client_name") or "Cliente",
        "client_address": row.get("client_address") or "",
        "store_id": row.get("store_id"),
        "store_name": row.get("store_name") or "",
        "courier_id": row.get("courier_id"),
        "items": items,
        "total": float(row.get("total") or 0),
        "payment": row.get("payment") or "Pix",
        "status": row.get("status") or "Pendente",
        "created_at": row.get("created_at") or "",
        "updated_at": row.get("updated_at") or "",
    }


try:
    _init_db()
except Exception as exc:
    app.logger.warning("Aviso na inicialização do banco: %s", exc)


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


@app.route("/manifest.json")
def manifest_json():
    return send_from_directory(app.static_folder, "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker_js():
    response = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


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
    client_address = str(payload.get("client_address") or "").strip()
    store_id = payload.get("store_id")
    store_name = str(payload.get("store_name") or "").strip()
    total = float(payload.get("total") or 0)
    payment = str(payload.get("payment") or "Pix").strip()

    if USE_POSTGRES:
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (
                        client_id, client_name, client_address,
                        store_id, store_name, courier_id,
                        items_json, total, payment, status, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s, 'Pendente', %s, %s)
                    RETURNING *;
                    """,
                    (
                        client_id,
                        client
