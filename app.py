import json
import os
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.environ.get("ROTASABOR_DATA_FILE", str(BASE_DIR / "orders.json")))

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "static"),
    template_folder=str(BASE_DIR / "templates"),
)


def _read_orders():
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_orders(orders):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return redirect(url_for("app_cliente"))


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


@app.route("/api/orders", methods=["GET", "POST"])
def orders_collection():
    orders = _read_orders()

    if request.method == "GET":
        return jsonify(orders), 200

    payload = request.get_json(silent=True) or {}
    items = payload.get("items") or []
    if not items:
        return jsonify({"error": "Carrinho vazio"}), 400

    next_id = max([int(o.get("id", 0)) for o in orders], default=0) + 1
    new_order = {
        "id": next_id,
        "items": items,
        "total": float(payload.get("total", 0) or 0),
        "payment": str(payload.get("payment") or "Pix"),
        "status": "Pendente",
    }
    orders.append(new_order)
    _write_orders(orders)
    return jsonify(new_order), 201


@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
def update_order(order_id):
    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status")
    if not new_status:
        return jsonify({"error": "Status obrigatório"}), 400

    orders = _read_orders()
    for order in orders:
        if int(order.get("id", 0)) == order_id:
            order["status"] = str(new_status)
            _write_orders(orders)
            return jsonify(order), 200

    return jsonify({"error": "Pedido não encontrado"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
