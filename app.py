from datetime import datetime
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Configuração padrão (ajuste conforme sua regra de negócio)
MIN_COURIER_PLATFORM_PCT = 8.0  # % mínima cobrada do entregador na aba/app dele

# Estruturas em memória (substitua ou sincronize com o seu banco SQLite/PostgreSQL)
ESTABLISHMENTS = []
PRODUCTS = []
AD_CHARGES = []
COURIERS = []
ORDERS = [
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
        "status": "Pronto para despacho",
        "released_to_couriers": True,
        "courier_accepted": False,
        "courier_id": None,
        "platform_pct_applied": MIN_COURIER_PLATFORM_PCT,
        "platform_courier_cut": 0.0,
        "courier_net_earning": 0.0,
        "created_at": datetime.now().isoformat(),
    }
]


@app.route("/estabelecimento")
def rota_portal_estabelecimento():
    return render_template("portal_estabelecimento.html")


@app.route("/api/establishments", methods=["GET", "POST"])
def api_establishments():
    if request.method == "GET":
        return jsonify(ESTABLISHMENTS)

    data = request.get_json(silent=True) or {}
    new_store = {
        "id": len(ESTABLISHMENTS) + 1,
        "store_name": (data.get("store_name") or "").strip(),
        "owner_name": (data.get("owner_name") or "").strip(),
        "cpf": (data.get("cpf") or "").strip(),
        "cnpj_mei": (data.get("cnpj_mei") or "").strip(),
        "address": (data.get("address") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "email": (data.get("email") or "").strip().lower(),
        "status": "Ativo",
        "created_at": datetime.now().isoformat(),
    }
    if not new_store["store_name"] or not new_store["cpf"]:
        return jsonify({"error": "Nome do estabelecimento e CPF são obrigatórios."}), 400

    ESTABLISHMENTS.append(new_store)
    return jsonify(new_store), 201


@app.route("/api/products", methods=["GET", "POST"])
def api_products():
    if request.method == "GET":
        # Ordena produtos impulsionados por propaganda primeiro para a vitrine do cliente
        ordered = sorted(PRODUCTS, key=lambda p: (0 if p.get("featured") else 1, -p["id"]))
        return jsonify(ordered)

    data = request.get_json(silent=True) or {}
    product = {
        "id": len(PRODUCTS) + 1,
        "store_id": data.get("store_id"),
        "store_name": (data.get("store_name") or "Estabelecimento").strip(),
        "store_address": (data.get("store_address") or "").strip(),
        "name": (data.get("name") or "").strip(),
        "price": float(data.get("price") or 0.0),
        "description": (data.get("description") or "").strip(),
        "featured": bool(data.get("featured", False)),
        "available": True,
    }
    if not product["name"] or product["price"] <= 0:
        return jsonify({"error": "Nome e preço válido são obrigatórios."}), 400

    PRODUCTS.append(product)
    return jsonify(product), 201


@app.route("/api/establishments/<int:store_id>/ads", methods=["GET", "POST"])
def api_establishment_ads(store_id):
    if request.method == "GET":
        return jsonify([c for c in AD_CHARGES if int(c["store_id"]) == store_id])

    data = request.get_json(silent=True) or {}
    charge = {
        "id": len(AD_CHARGES) + 1,
        "store_id": store_id,
        "package_name": (data.get("package_name") or "Impulso Vitrine").strip(),
        "amount": float(data.get("amount") or 0.0),
        "status": "Registrado",
        "created_at": datetime.now().isoformat(),
    }
    if charge["amount"] <= 0:
        return jsonify({"error": "Valor do pacote de propaganda inválido."}), 400

    AD_CHARGES.append(charge)
    return jsonify(charge), 201


@app.route("/api/orders", methods=["GET", "POST"])
def api_orders():
    if request.method == "GET":
        # Apenas pedidos soltos pelo estabelecimento entram na fila dos entregadores
        available_for_couriers = [o for o in ORDERS if o.get("released_to_couriers", True)]
        return jsonify(available_for_couriers)

    data = request.get_json(silent=True) or {}
    order_id = len(ORDERS) + 1
    fee = float(data.get("delivery_fee") or 0.0)
    pct = float(data.get("min_platform_pct") or MIN_COURIER_PLATFORM_PCT)
    platform_cut = round(fee * (pct / 100.0), 2)
    net_earning = round(max(0.0, fee - platform_cut), 2)

    order = {
        "id": order_id,
        "order_code": f"RS-{order_id:03d}",
        "store_id": data.get("store_id"),
        "store_name": (data.get("store_name") or "Estabelecimento").strip(),
        "client_name": (data.get("client_name") or "Cliente").strip(),
        "client_phone": (data.get("client_phone") or "").strip(),
        "client_address": (data.get("client_address") or "").strip(),
        "items_total": float(data.get("items_total") or 0.0),
        "delivery_fee": fee,
        "status": "Aguardando despacho da loja",
        "released_to_couriers": bool(data.get("released_to_couriers", False)),
        "courier_accepted": False,
        "courier_id": None,
        "platform_pct_applied": pct,
        "platform_courier_cut": platform_cut,
        "courier_net_earning": net_earning,
        "created_at": datetime.now().isoformat(),
    }
    ORDERS.append(order)
    return jsonify(order), 201


@app.route("/api/orders/<int:order_id>/dispatch", methods=["POST"])
def dispatch_order_to_couriers(order_id):
    order = next((o for o in ORDERS if int(o["id"]) == order_id), None)
    if not order:
        return jsonify({"error": "Pedido não encontrado."}), 404

    order["released_to_couriers"] = True
    order["status"] = "Disponível para entregadores"
    # Retorna apenas o status do pedido para a loja (sem dados dos entregadores)
    return jsonify({
        "id": order["id"],
        "order_code": order["order_code"],
        "status": order["status"],
        "released_to_couriers": True,
    })


@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
def update_order(order_id):
    order = next((o for o in ORDERS if int(o["id"]) == order_id), None)
    if not order:
        return jsonify({"error": "Pedido não encontrado."}), 404

    data = request.get_json(silent=True) or {}

    if "courier_id" in data:
        order["courier_id"] = data["courier_id"]
    if "courier_accepted" in data:
        order["courier_accepted"] = bool(data["courier_accepted"])
    if "status" in data:
        order["status"] = data["status"]

    if str(order.get("status", "")).lower() == "entregue":
        provided_code = "".join(ch for ch in str(data.get("delivery_code") or data.get("last4") or "") if ch.isdigit())
        expected_last4 = "".join(ch for ch in str(order.get("client_phone") or "") if ch.isdigit())[-4:]
        if expected_last4 and provided_code != expected_last4:
            return jsonify({"error": "Os 4 últimos números do celular do cliente não conferem."}), 400

        fee = float(order.get("delivery_fee") or 0.0)
        pct = float(order.get("platform_pct_applied") or MIN_COURIER_PLATFORM_PCT)
        cut = round(fee * (pct / 100.0), 2)
        order["platform_courier_cut"] = cut
        order["courier_net_earning"] = round(max(0.0, fee - cut), 2)

    return jsonify(order)


@app.route("/api/admin/overview", methods=["GET"])
def admin_overview():
    total_ads = round(sum(float(c.get("amount") or 0.0) for c in AD_CHARGES), 2)
    delivered = [o for o in ORDERS if str(o.get("status", "")).lower() == "entregue"]
    total_courier_cut = round(sum(float(o.get("platform_courier_cut") or 0.0) for o in delivered), 2)
    total_courier_net = round(sum(float(o.get("courier_net_earning") or 0.0) for o in delivered), 2)
    total_products_value = round(sum(float(o.get("items_total") or 0.0) for o in ORDERS), 2)
    total_delivery_fees = round(sum(float(o.get("delivery_fee") or 0.0) for o in ORDERS), 2)

    return jsonify({
        "my_total_earnings": round(total_ads + total_courier_cut, 2),
        "my_ads_earnings": total_ads,
        "my_courier_pct_earnings": total_courier_cut,
        "couriers_net_payout": total_courier_net,
        "gross_products_volume": total_products_value,
        "gross_delivery_fees": total_delivery_fees,
        "establishments_count": len(ESTABLISHMENTS),
        "products_count": len(PRODUCTS),
        "orders_count": len(ORDERS),
        "delivered_count": len(delivered),
        "history": ORDERS,
        "ad_charges": AD_CHARGES,
    })
