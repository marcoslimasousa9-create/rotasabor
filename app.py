import json
import os
from datetime import datetime
from flask import (
    Flask,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.path.join(DATA_DIR, "rotasabor_db.json")

BUILD_VERSION = "2026.11.25.133400"
BUILD_NOTES = (
    "RotaSabor na nuvem — Tema escuro #0b1220, persistencia em JSON, "
    "App Cliente, App Motoboy e atalho PWA prontos."
)

DEFAULT_DB = {
    "estabelecimentos": [
        {
            "id": 1,
            "nome": "Hamburgueria Centro",
            "categoria": "Lanches & Smash • Centro, Catanduva - SP",
            "avaliacao": "4.9",
            "tempo": "25-35 min",
            "taxa_entrega": 8.0,
            "promo": "Combo Smash + Fritas com 15% OFF",
            "cardapio": [
                {
                    "id": 101,
                    "nome": "Smash Duplo Bacon",
                    "preco": 28.0
                },
                {
                    "id": 102,
                    "nome": "Batata Rustica 300g",
                    "preco": 14.0
                },
                {
                    "id": 103,
                    "nome": "Refrigerante Lata",
                    "preco": 6.0
                }
            ]
        },
        {
            "id": 2,
            "nome": "Marmitaria Sabor da Casa",
            "categoria": "Refeicoes Caseiras • Catanduva - SP",
            "avaliacao": "4.8",
            "tempo": "30-45 min",
            "taxa_entrega": 7.0,
            "promo": "Marmita Executiva + Sobremesa",
            "cardapio": [
                {
                    "id": 201,
                    "nome": "Marmita Frango Grelhado G",
                    "preco": 24.0
                },
                {
                    "id": 202,
                    "nome": "Marmita Contra-File G",
                    "preco": 29.0
                }
            ]
        }
    ],
    "pedidos": [],
    "chamadas": [
        {
            "id": 1,
            "loja": "Hamburgueria Centro",
            "bairro": "Centro -> Jardim Alpino",
            "valor": 12.5,
            "status": "disponivel"
        },
        {
            "id": 2,
            "loja": "Marmitaria Sabor da Casa",
            "bairro": "Centro -> Vila Rodrigues",
            "valor": 10.0,
            "status": "disponivel"
        }
    ],
    "ganhos_resumo": {
        "entregas_concluidas": 0,
        "total_ganho": 0.0
    }
}


def load_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):
        save_db(DEFAULT_DB)
        return json.loads(json.dumps(DEFAULT_DB))
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        save_db(DEFAULT_DB)
        return json.loads(json.dumps(DEFAULT_DB))


def save_db(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return render_template(
        "app_cliente.html",
        build_version=BUILD_VERSION,
        build_notes=BUILD_NOTES,
    )


@app.route("/app-cliente")
def app_cliente():
    return render_template(
        "app_cliente.html",
        build_version=BUILD_VERSION,
        build_notes=BUILD_NOTES,
    )


@app.route("/app-motoboy")
def app_motoboy():
    return render_template(
        "app_motoboy.html",
        build_version=BUILD_VERSION,
        build_notes=BUILD_NOTES,
    )


@app.route("/manifest.json")
def manifest():
    return send_from_directory(STATIC_DIR, "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    resp = make_response(send_from_directory(STATIC_DIR, "sw.js", mimetype="application/javascript"))
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/api/atualizacoes")
def api_atualizacoes():
    apk_existe = os.path.exists(os.path.join(STATIC_DIR, "RotaSabor.apk"))
    return jsonify(
        {
            "versao": BUILD_VERSION,
            "notas": BUILD_NOTES,
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "download_pacote_url": "/download/pacote-app",
            "download_apk_url": "/download/apk" if apk_existe else None,
            "apk_disponivel": apk_existe,
        }
    )


@app.route("/download/pacote-app")
def download_pacote_app():
    html_content = render_template(
        "app_cliente.html",
        build_version=BUILD_VERSION,
        build_notes=BUILD_NOTES,
    )
    resp = make_response(html_content)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="RotaSabor-Cliente-v{BUILD_VERSION}.html"'
    return resp


@app.route("/download/apk")
def download_apk():
    apk_path = os.path.join(STATIC_DIR, "RotaSabor.apk")
    if not os.path.exists(apk_path):
        return (
            jsonify(
                {
                    "erro": "Arquivo static/RotaSabor.apk ainda nao foi adicionado.",
                    "dica": "Use o atalho PWA pelo navegador ou coloque RotaSabor.apk dentro da pasta static/.",
                }
            ),
            404,
        )
    return send_from_directory(
        STATIC_DIR,
        "RotaSabor.apk",
        as_attachment=True,
        download_name="RotaSabor.apk",
    )


@app.route("/api/estabelecimentos", methods=["GET"])
def get_estabelecimentos():
    db = load_db()
    return jsonify(db["estabelecimentos"])


@app.route("/api/pedidos", methods=["GET", "POST"])
def pedidos():
    db = load_db()
    if request.method == "GET":
        return jsonify(db["pedidos"])

    payload = request.get_json(force=True) or {}
    itens = payload.get("itens", [])
    loja_nome = payload.get("loja", "Hamburgueria Centro")
    pagamento = payload.get("pagamento", "Pix")
    total = float(payload.get("total", 0.0))

    novo_pedido = {
        "id": len(db["pedidos"]) + 1,
        "loja": loja_nome,
        "itens": itens,
        "pagamento": pagamento,
        "total": round(total, 2),
        "status": "Confirmado",
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    db["pedidos"].insert(0, novo_pedido)

    nova_chamada = {
        "id": len(db["chamadas"]) + 1,
        "loja": loja_nome,
        "bairro": "Entrega RotaSabor • Catanduva - SP",
        "valor": round(max(8.0, total * 0.25), 2),
        "status": "disponivel",
    }
    db["chamadas"].insert(0, nova_chamada)

    save_db(db)
    return jsonify({"ok": True, "pedido": novo_pedido}), 201


@app.route("/api/motoboy/estado", methods=["GET"])
def motoboy_estado():
    db = load_db()
    return jsonify(
        {
            "chamadas": db["chamadas"],
            "resumo": db["ganhos_resumo"],
        }
    )


@app.route("/api/motoboy/aceitar/<int:chamada_id>", methods=["POST"])
def aceitar_chamada(chamada_id):
    db = load_db()
    for ch in db["chamadas"]:
        if ch["id"] == chamada_id:
            ch["status"] = "em_andamento"
            save_db(db)
            return jsonify({"ok": True, "chamada": ch})
    return jsonify({"ok": False, "erro": "Chamada nao encontrada"}), 404


@app.route("/api/motoboy/concluir/<int:chamada_id>", methods=["POST"])
def concluir_chamada(chamada_id):
    db = load_db()
    for ch in db["chamadas"]:
        if ch["id"] == chamada_id and ch["status"] != "concluida":
            ch["status"] = "concluida"
            db["ganhos_resumo"]["entregas_concluidas"] += 1
            db["ganhos_resumo"]["total_ganho"] = round(
                db["ganhos_resumo"]["total_ganho"] + float(ch["valor"]), 2
            )
            save_db(db)
            return jsonify({"ok": True, "chamada": ch, "resumo": db["ganhos_resumo"]})
    return jsonify({"ok": False, "erro": "Chamada nao encontrada ou ja concluida"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
