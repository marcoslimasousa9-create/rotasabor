from datetime import datetime
import json
import os
import re
from flask import Flask, jsonify, render_template, request
from werkzeug.security import generate_password_hash

app = Flask(__name__)

# Parâmetros configuráveis da plataforma
MIN_COURIER_PLATFORM_PCT = 8.0  # % mínima cobrada sobre a taxa de entrega
DATA_FILE = os.environ.get("ROTASABOR_DATA_FILE", "rotasabor_data.json")


def _only_digits(val) -> str:
    return re.sub(r"\D", "", str(val or ""))


def _is_valid_cpf(cpf_raw) -> bool:
    cpf = _only_digits(cpf_raw)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    s1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = 11 - (s1 % 11)
    if d1 >= 10:
        d1 = 0
    if d1 != int(cpf[9]):
        return False
    s2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = 11 - (s2 % 11)
    if d2 >= 10:
        d2 = 0
    return d2 == int(cpf[10])


def _default_state() -> dict:
    return {
        "establishments": [
            {
                "id": 1,
                "store_name": "Hamburgueria Centro",
                "owner_name": "Responsável Exemplo",
                "cpf": "",
                "cnpj_mei": "",
                "category": "Lanches & Refeicoes",
                "city": "Catanduva - SP",
                "address": "Centro, Catanduva - SP",
                "default_delivery_fee": 8.00,
                "estimated_time": "25-35 min",
                "phone": "",
                "email": "",
                "status": "Ativo",
                "created_at": datetime.now().isoformat(),
            }
        ],
        "products": [],
        "ad_charges": [],
        "clients": [],
        "couriers": [],
        "orders": [
            {
                "id": 6,
                "order_code": "RS-006",
                "store_id": 1,
                "store_name": "Hamburgueria Centro",
                "client_name": "Cliente Exemplo",
                "client_phone": "17999991234",
                "client_address": "Rua Camanducaia, Catanduva - SP",
                "items_total": 45.00,
                "delivery_fee": 7.00,
                "status": "Disponível para entregadores",
                "released_to_couriers": True,
                "courier_accepted": False,
                "courier_id": None,
                "platform_pct_applied": MIN_COURIER_PLATFORM_PCT,
                "platform_courier_cut": round(7.00 * (MIN_COURIER_PLATFORM_PCT / 100.0), 2),
                "courier_net_earning": round(7.00 - (7.00 * (MIN_COURIER_PLATFORM_PCT / 100.0)), 2),
                "created_at": datetime.now().isoformat(),
                "delivered_at": None,
            }
        ],
    }


def _load_state() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                base = _default_state()
                for k, v in base.items():
                    if k not in data or not isinstance(data[k], list):
                        data[k] = v
                return data
        except Exception:
            pass
    state = _default_state()
    _save_state(state)
    return state


def _save_state(state: dict) -> None:
    try:
        folder = os.path.dirname(DATA_FILE)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


DB = _load_state()


def _next_id(items: list) -> int:
    if not items:
        return 1
    return max(int(x.get("id", 0)) for x in items) + 1


# =========================
# ROTAS DAS PÁGINAS (TEMPLATES)
# =========================

@app.route("/")
def index():
    return render_template("painel_gestao.html")


@app.route("/gestao")
def rota_gestao():
    return render_template("painel_gestao.html")


@app.route("/estabelecimento")
def rota_estabelecimento():
    return render_template("portal_estabelecimento.html")


@app.route("/cliente")
def rota_cliente():
    return render_template("app_cliente.html")


@app.route("/motoboy")
def rota_motoboy():
    return render_template("app_motoboy.html")


# =========================
# ESTABELECIMENTOS, PRODUTOS E PROPAGANDA
# =========================

@app.route("/api/establishments", methods=["GET", "POST"])
def api_establishments():
    if request.method == "GET":
        # Remove hash de senha ao expor registros
        safe = [{k: v for k, v in s.items() if k != "password_hash"} for s in DB["establishments"]]
        return jsonify(safe)

    data = request.get_json(silent=True) or {}
    store_name = (data.get("store_name") or data.get("name") or "").strip()
    cpf_clean = _only_digits(data.get("cpf"))
    mei_clean = _only_digits(data.get("cnpj_mei") or data.get("mei"))

    if not store_name:
        return jsonify({"error": "Nome do estabelecimento é obrigatório."}), 400

    # Exige CPF válido quando enviado pelo cadastro completo do portal
    if cpf_clean and not _is_valid_cpf(cpf_clean):
        return jsonify({"error": "CPF inválido. Verifique os 11 dígitos."}), 400

    password_raw = (data.get("password") or "").strip()
    store = {
        "id": _next_id(DB["establishments"]),
        "store_name": store_name,
        "owner_name": (data.get("owner_name") or "").strip(),
        "cpf": cpf_clean,
        "cnpj_mei": mei_clean,
        "category": (data.get("category") or "Lanches & Refeicoes").strip(),
        "city": (data.get("city") or "Catanduva - SP").strip(),
        "address": (data.get("address") or data.get("city") or "").strip(),
        "default_delivery_fee": float(data.get("delivery_fee") or data.get("default_delivery_fee") or 8.0),
        "estimated_time": (data.get("estimated_time") or "25-35 min").strip(),
        "phone": _only_digits(data.get("phone")),
        "email": (data.get("email") or "").strip().lower(),
        "password_hash": generate_password_hash(password_raw) if password_raw else None,
        "status": "Ativo",
        "created_at": datetime.now().isoformat(),
    }
    DB["establishments"].append(store)
    _save_state(DB)

    out = {k: v for k, v in store.items() if k != "password_hash"}
    return jsonify(out), 201


@app.route("/api/products", methods=["GET", "POST"])
def api_products():
    if request.method == "GET":
        store_id = request.args.get("store_id")
        items = DB["products"]
        if store_id is not None:
            items = [p for p in items if str(p.get("store_id")) == str(store_id)]
        ordered = sorted(items, key=lambda p: (0 if p.get("featured") else 1, -int(p.get("id", 0))))
        return jsonify(ordered)

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    price = float(data.get("price") or 0.0)
    if not name or price <= 0:
        return jsonify({"error": "Informe nome e preço maior que zero."}), 400

    product = {
        "id": _next_id(DB["products"]),
        "store_id": data.get("store_id"),
        "store_name": (data.get("store_name") or "Estabelecimento").strip(),
        "store_address": (data.get("store_address") or "").strip(),
        "name": name,
        "price": round(price, 2),
        "description": (data.get("description") or "").strip(),
        "featured": bool(data.get("featured", False)),
        "available": bool(data.get("available", True)),
        "created_at": datetime.now().isoformat(),
    }
    DB["products"].append(product)
    _save_state(DB)
    return jsonify(product), 201


@app.route("/api/establishments/<int:store_id>/ads", methods=["GET", "POST"])
def api_establishment_ads(store_id):
    if request.method == "GET":
        return jsonify([c for c in DB["ad_charges"] if int(c.get("store_id", 0)) == store_id])

    data = request.get_json(silent=True) or {}
    amount = float(data.get("amount") or 0.0)
    if amount <= 0:
        return jsonify({"error": "Valor do pacote de propaganda inválido."}), 400

    charge = {
        "id": _next_id(DB["ad_charges"]),
        "store_id": store_id,
        "package_name": (data.get("package_name") or "Impulso Vitrine").strip(),
        "amount": round(amount, 2),
        "status": "Registrado",
        "created_at": datetime.now().isoformat(),
    }
    DB["ad_charges"].append(charge)

    # Marca produtos da loja como destaque quando há pacote de propaganda
    for p in DB["products"]:
        if p.get("store_id") == store_id:
            p["featured"] = True

    _save_state(DB)
    return jsonify(charge), 201


# =========================
# CLIENTES E ENTREGADORES (CADASTRO OBRIGATÓRIO)
# =========================

@app.route("/api/clients", methods=["GET", "POST"])
def api_clients():
    if request.method == "GET":
        safe = [{k: v for k, v in c.items() if k != "password_hash"} for c in DB["clients"]]
        return jsonify(safe)

    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or data.get("name") or "").strip()
    phone = _only_digits(data.get("phone"))
    if not full_name or len(phone) < 8:
        return jsonify({"error": "Nome e telefone válido são obrigatórios para o cliente."}), 400

    password_raw = (data.get("password") or "").strip()
    client = {
        "id": _next_id(DB["clients"]),
        "full_name": full_name,
        "cpf": _only_digits(data.get("cpf")),
        "phone": phone,
        "email": (data.get("email") or "").strip().lower(),
        "default_address": (data.get("address") or data.get("default_address") or "").strip(),
        "password_hash": generate_password_hash(password_raw) if password_raw else None,
        "created_at": datetime.now().isoformat(),
    }
    DB["clients"].append(client)
    _save_state(DB)
    return jsonify({k: v for k, v in client.items() if k != "password_hash"}), 201


@app.route("/api/couriers", methods=["GET", "POST"])
def api_couriers():
    if request.method == "GET":
        safe = [{k: v for k, v in c.items() if k != "password_hash"} for c in DB["couriers"]]
        return jsonify(safe)

    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or data.get("name") or "").strip()
    cpf_clean = _only_digits(data.get("cpf"))
    phone = _only_digits(data.get("phone"))

    if not full_name or not _is_valid_cpf(cpf_clean) or len(phone) < 8:
        return jsonify({"error": "Nome, CPF válido e telefone são obrigatórios para o entregador."}), 400

    password_raw = (data.get("password") or "").strip()
    courier = {
        "id": _next_id(DB["couriers"]),
        "full_name": full_name,
        "cpf": cpf_clean,
        "phone": phone,
        "vehicle": (data.get("vehicle") or "Moto").strip(),
        "email": (data.get("email") or "").strip().lower(),
        "min_platform_pct": float(data.get("min_platform_pct") or MIN_COURIER_PLATFORM_PCT),
        "password_hash": generate_password_hash(password_raw) if password_raw else None,
        "status": "Ativo",
        "created_at": datetime.now().isoformat(),
    }
    DB["couriers"].append(courier)
    _save_state(DB)
    return jsonify({k: v for k, v in courier.items() if k != "password_hash"}), 201


# =========================
# PEDIDOS, SOLTURA PELA LOJA E ENTREGA
# =========================

@app.route("/api/orders", methods=["GET", "POST"])
def api_orders():
    if request.method == "GET":
        store_id = request.args.get("store_id")
        if store_id is not None:
            # Visão do estabelecimento: apenas pedidos da loja, SEM dados internos de entregadores
            store_orders = []
            for o in DB["orders"]:
                if str(o.get("store_id")) == str(store_id):
                    store_orders.append({
                        "id": o["id"],
                        "order_code": o.get("order_code"),
                        "store_id": o.get("store_id"),
                        "store_name": o.get("store_name"),
                        "client_name": o.get("client_name"),
                        "client_address": o.get("client_address"),
                        "items_total": o.get("items_total"),
                        "delivery_fee": o.get("delivery_fee"),
                        "status": o.get("status"),
                        "released_to_couriers": o.get("released_to_couriers", False),
                        "created_at": o.get("created_at"),
                    })
            return jsonify(store_orders)

        # Visão dos entregadores: pedidos soltos pela loja
        released = [o for o in DB["orders"] if o.get("released_to_couriers", False)]
        return jsonify(released)

    data = request.get_json(silent=True) or {}
    order_id = _next_id(DB["orders"])
    fee = round(float(data.get("delivery_fee") or 0.0), 2)
    items_total = round(float(data.get("items_total") or 0.0), 2)
    pct = float(data.get("min_platform_pct") or MIN_COURIER_PLATFORM_PCT)
    cut = round(fee * (pct / 100.0), 2)
    net = round(max(0.0, fee - cut), 2)

    order = {
        "id": order_id,
        "order_code": f"RS-{order_id:03d}",
        "store_id": data.get("store_id"),
        "store_name": (data.get("store_name") or "Estabelecimento").strip(),
        "client_name": (data.get("client_name") or "Cliente").strip(),
        "client_phone": _only_digits(data.get("client_phone")),
        "client_address": (data.get("client_address") or "").strip(),
        "items_total": items_total,
        "delivery_fee": fee,
        "status": data.get("status") or "Aguardando despacho da loja",
        "released_to_couriers": bool(data.get("released_to_couriers", False)),
        "courier_accepted": False,
        "courier_id": None,
        "platform_pct_applied": pct,
        "platform_courier_cut": cut,
        "courier_net_earning": net,
        "created_at": datetime.now().isoformat(),
        "delivered_at": None,
    }
    DB["orders"].append(order)
    _save_state(DB)
    return jsonify(order), 201


@app.route("/api/orders/<int:order_id>/dispatch", methods=["POST"])
def dispatch_order(order_id):
    order = next((o for o in DB["orders"] if int(o.get("id", 0)) == order_id), None)
    if not order:
        return jsonify({"error": "Pedido não encontrado."}), 404

    order["released_to_couriers"] = True
    order["status"] = "Disponível para entregadores"
    _save_state(DB)

    # Retorna à loja apenas o despacho confirmado, sem dados dos entregadores
    return jsonify({
        "id": order["id"],
        "order_code": order["order_code"],
        "status": order["status"],
        "released_to_couriers": True,
    })


@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
def patch_order(order_id):
    order = next((o for o in DB["orders"] if int(o.get("id", 0)) == order_id), None)
    if not order:
        return jsonify({"error": "Pedido não encontrado."}), 404

    data = request.get_json(silent=True) or {}

    if "courier_id" in data:
        order["courier_id"] = data["courier_id"]
    if "courier_accepted" in data:
        order["courier_accepted"] = bool(data["courier_accepted"])
        if order["courier_accepted"] and str(order.get("status", "")).lower() != "entregue":
            order["status"] = "Aceito pelo entregador"
    if "status" in data:
        order["status"] = str(data["status"]).strip()

    if str(order.get("status", "")).lower() == "entregue":
        provided_last4 = _only_digits(data.get("delivery_code") or data.get("last4"))
        expected_last4 = _only_digits(order.get("client_phone"))[-4:]
        if expected_last4 and provided_last4 and provided_last4 != expected_last4:
            return jsonify({"error": "Os 4 últimos dígitos do celular do cliente não conferem."}), 400

        fee = float(order.get("delivery_fee") or 0.0)
        pct = float(order.get("platform_pct_applied") or MIN_COURIER_PLATFORM_PCT)
        cut = round(fee * (pct / 100.0), 2)
        order["platform_courier_cut"] = cut
        order["courier_net_earning"] = round(max(0.0, fee - cut), 2)
        if not order.get("delivered_at"):
            order["delivered_at"] = datetime.now().isoformat()

    _save_state(DB)
    return jsonify(order)


# =========================
# PAINEL DE GESTÃO (EXCLUSIVO DO DONO)
# =========================

@app.route("/api/admin/overview", methods=["GET"])
def api_admin_overview():
    total_ads = round(sum(float(c.get("amount") or 0.0) for c in DB["ad_charges"]), 2)
    delivered = [o for o in DB["orders"] if str(o.get("status", "")).lower() == "entregue"]
    total_courier_cut = round(sum(float(o.get("platform_courier_cut") or 0.0) for o in delivered), 2)
    total_courier_net = round(sum(float(o.get("courier_net_earning") or 0.0) for o in delivered), 2)
    gross_items = round(sum(float(o.get("items_total") or 0.0) for o in DB["orders"]), 2)
    gross_fees = round(sum(float(o.get("delivery_fee") or 0.0) for o in DB["orders"]), 2)

    return jsonify({
        "my_total_earnings": round(total_ads + total_courier_cut, 2),
        "my_ads_earnings": total_ads,
        "my_courier_pct_earnings": total_courier_cut,
        "couriers_net_payout": total_courier_net,
        "gross_items_volume": gross_items,
        "gross_delivery_fees": gross_fees,
        "counts": {
            "establishments": len(DB["establishments"]),
            "products": len(DB["products"]),
            "clients": len(DB["clients"]),
            "couriers": len(DB["couriers"]),
            "orders": len(DB["orders"]),
            "delivered": len(delivered),
        },
        "orders_history": DB["orders"],
        "ad_charges_history": DB["ad_charges"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
