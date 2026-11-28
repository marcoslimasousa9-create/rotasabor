import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from jinja2 import TemplateNotFound
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# ---------------------------------------------------------------- configuração
database_url = os.environ.get("DATABASE_URL", "sqlite:///rotasabor.db")
for _prefix in ("postgres://", "postgresql://"):
    if database_url.startswith(_prefix):  # driver psycopg (v3) do requirements.txt
        database_url = "postgresql+psycopg://" + database_url[len(_prefix):]
        break

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

app.config.update(
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
    MAX_CONTENT_LENGTH=64 * 1024,
)

db = SQLAlchemy(app)

PAYMENTS = {"Dinheiro", "Cartão na entrega"}
STATUSES = {"Aguardando entregador", "Aceito pelo entregador", "Em rota", "Entregue", "Cancelado"}


# --------------------------------------------------------------------- modelos
class Establishment(db.Model):
    __tablename__ = "establishments"
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(140), nullable=False)
    category = db.Column(db.String(80), default="Lanches & Refeições")
    default_delivery_fee = db.Column(db.Float, default=8.0)
    estimated_time = db.Column(db.String(40), default="25-35 min")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "store_name": self.store_name,
            "category": self.category,
            "default_delivery_fee": self.default_delivery_fee,
            "estimated_time": self.estimated_time,
        }


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    establishment_id = db.Column(db.Integer, db.ForeignKey("establishments.id"), nullable=True)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.String(255), default="")
    price = db.Column(db.Float, nullable=False, default=0.0)
    featured = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "establishment_id": self.establishment_id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "featured": self.featured,
        }


class Courier(db.Model):
    __tablename__ = "couriers"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(140), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    cpf = db.Column(db.String(20), nullable=True)
    vehicle = db.Column(db.String(80), default="Moto")
    plate = db.Column(db.String(20), default="")
    status = db.Column(db.String(40), default="Offline")
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        cpf = self.cpf or ""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "cpf": f"***{cpf[-2:]}" if cpf else None,  # CPF nunca sai completo
            "vehicle": self.vehicle,
            "plate": self.plate,
            "status": self.status,
            "lat": self.lat,
            "lng": self.lng,
            "active": self.active is not False,
        }


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(30), nullable=False)
    store_id = db.Column(db.Integer, nullable=True)
    store_name = db.Column(db.String(140), default="Estabelecimento")
    client_name = db.Column(db.String(140), nullable=False)
    client_phone = db.Column(db.String(40), nullable=False)
    client_address = db.Column(db.String(255), nullable=False)
    items_total = db.Column(db.Float, default=0.0)
    delivery_fee = db.Column(db.Float, default=0.0)
    courier_net_earning = db.Column(db.Float, default=0.0)
    courier_id = db.Column(db.Integer, db.ForeignKey("couriers.id"), nullable=True)
    courier_accepted = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(60), default="Aguardando entregador")
    payment_method = db.Column(db.String(40), default="Dinheiro")
    payment_status = db.Column(db.String(30), default="Pendente")
    items_json = db.Column(db.Text, default="[]")
    tracking_token = db.Column(db.String(64), nullable=True)
    delivery_code = db.Column(db.String(4), nullable=True)
    delivery_attempts = db.Column(db.Integer, default=0)
    delivered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def order_dict(o, view):
    """Cada perfil enxerga só o que precisa (view: admin | courier_open | courier_mine | customer)."""
    d = {k: getattr(o, k) for k in (
        "id", "order_code", "store_id", "store_name", "client_address", "items_total",
        "delivery_fee", "courier_net_earning", "courier_id", "courier_accepted", "status")}
    d["created_at"] = o.created_at.isoformat() if o.created_at else None
    if view in ("admin", "courier_mine", "customer"):
        d["client_name"] = o.client_name
        d["payment_method"] = o.payment_method
        d["items"] = json.loads(o.items_json or "[]")
    if view in ("admin", "courier_mine"):
        d["client_phone"] = o.client_phone
    if view in ("admin", "customer"):
        d["delivery_code"] = o.delivery_code  # o entregador NUNCA recebe o código
    if view == "admin":
        d["payment_status"] = o.payment_status
    return d


# --------------------------------------------------------------------- helpers
def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _num(v, default=0.0):
    try:
        return round(float(str(v).replace(",", ".")), 2)
    except (TypeError, ValueError):
        return default


def clean(value, n=140):
    """Texto vindo de usuário: remove caracteres que permitem injetar HTML/JS nas telas."""
    s = str(value or "").strip()[:n]
    s = re.sub(r"[<>]", "", s)
    s = re.sub(r"\s*&\s*", " e ", s)
    s = s.replace("'", "’").replace('"', "”").replace("`", "’").replace("\\", "/")
    return s.strip()


def _same(a, b):
    return hmac.compare_digest(str(a).encode(), str(b).encode())


_hits = {}


def too_many(key, limit, window):
    now = time.time()
    if len(_hits) > 5000:
        _hits.clear()
    hits = [t for t in _hits.get(key, []) if now - t < window] + [now]
    _hits[key] = hits
    return len(hits) > limit


def client_ip():
    return (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()


def role_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **k):
            if session.get("role") not in roles:
                return jsonify({"error": "Acesso não autorizado."}), 401
            return f(*a, **k)
        return wrapper
    return deco


def current_courier():
    if session.get("role") != "courier":
        return None
    c = db.session.get(Courier, session.get("uid"))
    return c if c and c.active is not False else None


@app.before_request
def _csrf_guard():
    # Só JSON é aceito em escritas: formulários de outros sites não conseguem enviar JSON.
    if (request.method in ("POST", "PATCH", "PUT", "DELETE") and request.path.startswith("/api/")
            and request.path != "/api/logout" and not request.is_json):
        return jsonify({"error": "Requisição inválida."}), 415


@app.after_request
def _headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------------- schema
def _ensure_schema():
    """Cria tabelas e adiciona colunas que faltam em tabelas antigas (causa do erro de estabelecimentos)."""
    db.create_all()
    insp = inspect(db.engine)
    pg = db.engine.dialect.name == "postgresql"
    legacy = {("couriers", "full_name"): "name", ("establishments", "store_name"): "name"}
    with db.engine.begin() as conn:
        for table in db.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"]: c for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = col.type.compile(dialect=db.engine.dialect)
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {'IF NOT EXISTS ' if pg else ''}{col.name} {ddl}"))
                old = legacy.get((table.name, col.name))
                if old and old in have:
                    conn.execute(text(f"UPDATE {table.name} SET {col.name} = {old} WHERE {col.name} IS NULL"))
            if pg:  # colunas antigas obrigatórias que o modelo atual não preenche
                for name, info in have.items():
                    if name not in table.columns and not info["nullable"] and info.get("default") is None:
                        conn.execute(text(f'ALTER TABLE {table.name} ALTER COLUMN "{name}" DROP NOT NULL'))


def _render_safe(template_name):
    try:
        return render_template(template_name)
    except TemplateNotFound:
        return f"Template '{template_name}' não encontrado.", 404


with app.app_context():
    _ensure_schema()

if not ADMIN_PASSWORD:
    print("[AVISO] ADMIN_PASSWORD não definida: o painel de administração fica bloqueado.")
if not os.environ.get("SECRET_KEY"):
    print("[AVISO] SECRET_KEY não definida: defina no Render, senão os logins caem a cada reinício.")


# ----------------------------------------------------------------------- páginas
@app.get("/")
def home():
    return redirect("/cliente")


@app.get("/login")
def login_page():
    return _render_safe("login.html")


@app.get("/painel")
@app.get("/painel_gestao.html")
def painel():
    if session.get("role") != "admin":
        return redirect("/login")
    return _render_safe("painel_gestao.html")


@app.get("/cliente")
@app.get("/app_cliente")
@app.get("/app_cliente.html")
@app.get("/cliente.html")
def app_cliente():
    return _render_safe("app_cliente.html")


@app.get("/motoboy")
@app.get("/app_motoboy")
@app.get("/app_motoboy.html")
@app.get("/entregador")
def app_motoboy():
    if session.get("role") != "courier":
        return redirect("/login")
    return _render_safe("app_motoboy.html")


# -------------------------------------------------------------------------- auth
@app.post("/api/login")
def login():
    if too_many(f"login:{client_ip()}", 10, 900):
        return jsonify({"error": "Muitas tentativas. Aguarde alguns minutos."}), 429
    d = request.get_json(silent=True) or {}
    ident = str(d.get("user") or "").strip()
    pwd = str(d.get("password") or "")

    if ADMIN_PASSWORD and _same(ident.lower(), ADMIN_USER.lower()) and _same(pwd, ADMIN_PASSWORD):
        session.clear()
        session.update(role="admin", uid=0, name="Admin")
        session.permanent = True
        return jsonify({"role": "admin", "redirect": "/painel"})

    phone = _digits(ident)
    if len(phone) >= 8:
        for c in Courier.query.all():
            if (_digits(c.phone) == phone and c.password_hash and c.active is not False
                    and check_password_hash(c.password_hash, pwd)):
                session.clear()
                session.update(role="courier", uid=c.id, name=c.full_name)
                session.permanent = True
                return jsonify({"role": "courier", "redirect": "/motoboy"})
    return jsonify({"error": "Usuário ou senha incorretos."}), 401


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    return jsonify({"role": session.get("role"), "name": session.get("name")})


# ---------------------------------------------------------- estabelecimentos/produtos
@app.get("/api/establishments")
def list_establishments():
    rows = Establishment.query.order_by(Establishment.id.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@app.post("/api/establishments")
@role_required("admin")
def create_establishment():
    d = request.get_json(silent=True) or {}
    store_name = clean(d.get("store_name") or d.get("name"))
    fee = _num(d.get("default_delivery_fee") or d.get("delivery_fee"), 8.0)
    if not store_name:
        return jsonify({"error": "Informe o nome do estabelecimento."}), 400
    if not 0 <= fee <= 50:
        return jsonify({"error": "Taxa de entrega inválida."}), 400
    est = Establishment(
        store_name=store_name,
        category=clean(d.get("category"), 80) or "Lanches & Refeições",
        default_delivery_fee=fee,
        estimated_time=clean(d.get("estimated_time"), 40) or "25-35 min",
    )
    db.session.add(est)
    db.session.commit()
    return jsonify(est.to_dict()), 201


@app.get("/api/products")
def list_products():
    rows = Product.query.order_by(Product.id.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@app.post("/api/products")
@role_required("admin")
def create_product():
    d = request.get_json(silent=True) or {}
    name = clean(d.get("name"))
    est = db.session.get(Establishment, _int(d.get("establishment_id")))
    price = _num(d.get("price"), -1)
    if not name or not est:
        return jsonify({"error": "Informe o nome do produto e o estabelecimento."}), 400
    if not 0.5 <= price <= 5000:
        return jsonify({"error": "Preço inválido."}), 400
    prod = Product(establishment_id=est.id, name=name, description=clean(d.get("description"), 255),
                   price=price, featured=bool(d.get("featured", False)))
    db.session.add(prod)
    db.session.commit()
    return jsonify(prod.to_dict()), 201


# ------------------------------------------------------------------- entregadores
@app.get("/api/couriers")
@role_required("admin", "courier")
def list_couriers():
    if session["role"] == "courier":
        c = current_courier()
        return jsonify([c.to_dict()] if c else [])
    return jsonify([c.to_dict() for c in Courier.query.order_by(Courier.id.desc()).all()])


@app.post("/api/couriers")
@role_required("admin")
def create_courier():
    d = request.get_json(silent=True) or {}
    full_name = clean(d.get("full_name") or d.get("name"))
    phone = _digits(d.get("phone") or d.get("whatsapp"))
    cpf = _digits(d.get("cpf"))
    pwd = str(d.get("password") or "") or f"{secrets.randbelow(10**6):06d}"
    if not full_name:
        return jsonify({"error": "Informe o nome do entregador."}), 400
    if len(phone) < 10:
        return jsonify({"error": "Informe o telefone com DDD."}), 400
    if cpf and len(cpf) != 11:
        return jsonify({"error": "CPF inválido."}), 400
    if len(pwd) < 6:
        return jsonify({"error": "A senha precisa ter ao menos 6 caracteres."}), 400
    if any(_digits(c.phone) == phone for c in Courier.query.all()):
        return jsonify({"error": "Já existe entregador com este telefone."}), 409
    c = Courier(full_name=full_name, phone=phone, cpf=cpf or None,
                vehicle=clean(d.get("vehicle"), 80) or "Moto", plate=clean(d.get("plate"), 20).upper(),
                status=clean(d.get("status"), 40) or "Offline",
                password_hash=generate_password_hash(pwd), active=True)
    db.session.add(c)
    db.session.commit()
    out = c.to_dict()
    out["initial_password"] = pwd  # mostrado uma única vez
    return jsonify(out), 201


@app.post("/api/couriers/<int:cid>/reset-password")
@role_required("admin")
def reset_courier_password(cid):
    c = db.get_or_404(Courier, cid)
    pwd = f"{secrets.randbelow(10**6):06d}"
    c.password_hash = generate_password_hash(pwd)
    db.session.commit()
    return jsonify({"initial_password": pwd})


# --------------------------------------------------------------------- pedidos
@app.get("/api/orders")
@role_required("admin", "courier")
def list_orders():
    if session["role"] == "admin":
        rows = Order.query.order_by(Order.id.desc()).limit(500).all()
        return jsonify([order_dict(o, "admin") for o in rows])
    c = current_courier()
    if not c:
        return jsonify({"error": "Acesso não autorizado."}), 401
    mine = (Order.query.filter(Order.courier_id == c.id, Order.status != "Cancelado")
            .order_by(Order.id.desc()).limit(200).all())
    open_ = (Order.query.filter(Order.courier_id.is_(None), Order.status == "Aguardando entregador")
             .order_by(Order.id.desc()).limit(50).all())
    return jsonify([order_dict(o, "courier_mine") for o in mine] + [order_dict(o, "courier_open") for o in open_])


@app.post("/api/orders")
def create_order():
    if too_many(f"order:{client_ip()}", 6, 900):
        return jsonify({"error": "Muitos pedidos seguidos. Tente novamente em alguns minutos."}), 429
    d = request.get_json(silent=True) or {}
    name = clean(d.get("client_name"))
    phone = _digits(d.get("client_phone"))
    addr = clean(d.get("client_address"), 255)
    pay = d.get("payment_method")
    if not name or not 10 <= len(phone) <= 13 or len(addr) < 8:
        return jsonify({"error": "Preencha nome, celular com DDD e endereço completo."}), 400
    if pay not in PAYMENTS:
        return jsonify({"error": "Forma de pagamento indisponível."}), 400

    raw = d.get("items")
    if not isinstance(raw, list) or not raw or len(raw) > 30:
        return jsonify({"error": "Sacola vazia."}), 400
    qty = {}
    for it in raw:
        if isinstance(it, dict):
            pid, q = _int(it.get("id")), _int(it.get("qty"))
            if pid and 1 <= q <= 20:
                qty[pid] = qty.get(pid, 0) + q
    prods = Product.query.filter(Product.id.in_(list(qty))).all() if qty else []
    stores = {p.establishment_id for p in prods}
    est = db.session.get(Establishment, next(iter(stores))) if len(stores) == 1 and None not in stores else None
    if not qty or len(prods) != len(qty) or not est:
        return jsonify({"error": "Itens inválidos. Atualize a página e monte a sacola de novo."}), 400

    # preços e taxa vêm do banco, nunca do navegador
    lines = [{"id": p.id, "name": p.name, "price": p.price, "qty": qty[p.id]} for p in prods]
    order = Order(
        order_code="tmp", store_id=est.id, store_name=est.store_name,
        client_name=name, client_phone=phone, client_address=addr,
        items_total=round(sum(l["price"] * l["qty"] for l in lines), 2),
        delivery_fee=round(est.default_delivery_fee or 0, 2),
        courier_net_earning=round(est.default_delivery_fee or 0, 2),
        status="Aguardando entregador", payment_method=pay, payment_status="Pendente",
        items_json=json.dumps(lines, ensure_ascii=False),
        tracking_token=secrets.token_urlsafe(24), delivery_code=f"{secrets.randbelow(10000):04d}",
    )
    db.session.add(order)
    db.session.flush()
    order.order_code = f"RS-{order.id:03d}"
    db.session.commit()
    out = order_dict(order, "customer")
    out["tracking_token"] = order.tracking_token
    return jsonify(out), 201


@app.get("/api/orders/track")
def track_orders():
    tokens = [t for t in request.args.get("tokens", "").split(",") if t][:20]
    rows = Order.query.filter(Order.tracking_token.in_(tokens)).order_by(Order.id.desc()).all() if tokens else []
    return jsonify([order_dict(o, "customer") for o in rows])


@app.patch("/api/orders/<int:order_id>")
@role_required("admin", "courier")
def update_order(order_id):
    order = db.get_or_404(Order, order_id)
    d = request.get_json(silent=True) or {}
    status = clean(d.get("status"), 60)

    if session["role"] == "admin":
        if "courier_id" in d:
            order.courier_id = _int(d["courier_id"]) or None
        if "courier_accepted" in d:
            order.courier_accepted = bool(d["courier_accepted"])
        if status:
            if status not in STATUSES:
                return jsonify({"error": "Status inválido."}), 400
            order.status = status
            if status == "Entregue":
                order.delivered_at = datetime.utcnow()
        db.session.commit()
        return jsonify(order_dict(order, "admin"))

    c = current_courier()
    if not c:
        return jsonify({"error": "Acesso não autorizado."}), 401

    if d.get("courier_accepted") is True:  # aceite atômico: só um entregador leva o pedido
        if order.courier_id == c.id:
            return jsonify(order_dict(order, "courier_mine"))
        n = (Order.query.filter(Order.id == order_id, Order.courier_id.is_(None),
                                Order.status == "Aguardando entregador")
             .update({"courier_id": c.id, "courier_accepted": True, "status": "Aceito pelo entregador"}))
        db.session.commit()
        if not n:
            return jsonify({"error": "Este pedido já foi aceito por outro entregador."}), 409
        db.session.refresh(order)
        return jsonify(order_dict(order, "courier_mine"))

    if order.courier_id != c.id:
        return jsonify({"error": "Este pedido não é seu."}), 403

    if status == "Em rota" and order.status in ("Aceito pelo entregador", "Em rota"):
        order.status = "Em rota"
    elif status == "Entregue":
        if order.status != "Entregue":
            if (order.delivery_attempts or 0) >= 5:
                return jsonify({"error": "Código bloqueado por tentativas. Fale com o suporte."}), 429
            if not (order.delivery_code and _same(_digits(d.get("delivery_code")), order.delivery_code)):
                order.delivery_attempts = (order.delivery_attempts or 0) + 1
                db.session.commit()
                return jsonify({"error": "Código incorreto."}), 400
            order.status = "Entregue"
            order.delivered_at = datetime.utcnow()
    else:
        return jsonify({"error": "Ação não permitida."}), 400
    db.session.commit()
    return jsonify(order_dict(order, "courier_mine"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
