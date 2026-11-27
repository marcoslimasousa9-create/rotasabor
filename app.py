import os
import re
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "sqlite:///rotasabor.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "cpf": self.cpf,
            "vehicle": self.vehicle,
            "plate": self.plate,
            "status": self.status,
            "lat": self.lat,
            "lng": self.lng,
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "order_code": self.order_code,
            "store_id": self.store_id,
            "store_name": self.store_name,
            "client_name": self.client_name,
            "client_phone": self.client_phone,
            "client_address": self.client_address,
            "items_total": self.items_total,
            "delivery_fee": self.delivery_fee,
            "courier_net_earning": self.courier_net_earning,
            "courier_id": self.courier_id,
            "courier_accepted": self.courier_accepted,
            "status": self.status,
        }


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _ensure_schema():
    db.create_all()
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name
    if "couriers" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("couriers")}
        alter_statements = []
        if "full_name" not in existing_cols:
            col_type = "VARCHAR(140)" if dialect == "postgresql" else "VARCHAR(140)"
            alter_statements.append(f"ALTER TABLE couriers ADD COLUMN full_name {col_type}")
        if "cpf" not in existing_cols:
            alter_statements.append("ALTER TABLE couriers ADD COLUMN cpf VARCHAR(20)")
        if "lat" not in existing_cols:
            lat_type = "DOUBLE PRECISION" if dialect == "postgresql" else "FLOAT"
            alter_statements.append(f"ALTER TABLE couriers ADD COLUMN lat {lat_type}")
        if "lng" not in existing_cols:
            lng_type = "DOUBLE PRECISION" if dialect == "postgresql" else "FLOAT"
            alter_statements.append(f"ALTER TABLE couriers ADD COLUMN lng {lng_type}")
        if "created_at" not in existing_cols:
            dt_type = "TIMESTAMP WITHOUT TIME ZONE" if dialect == "postgresql" else "DATETIME"
            alter_statements.append(f"ALTER TABLE couriers ADD COLUMN created_at {dt_type}")

        if dialect == "postgresql" and "name" in existing_cols:
            alter_statements.append("ALTER TABLE couriers ALTER COLUMN name DROP NOT NULL")

        if alter_statements:
            with db.engine.begin() as conn:
                for stmt in alter_statements:
                    conn.execute(text(stmt))
                if "name" in existing_cols and "full_name" in existing_cols:
                    conn.execute(text("UPDATE couriers SET full_name = name WHERE full_name IS NULL AND name IS NOT NULL"))
                    conn.execute(text("UPDATE couriers SET name = full_name WHERE name IS NULL AND full_name IS NOT NULL"))


def _sync_legacy_courier_name(courier_id, full_name):
    inspector = inspect(db.engine)
    if "couriers" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("couriers")}
        if "name" in existing_cols and courier_id is not None:
            db.session.execute(
                text("UPDATE couriers SET name = :full_name WHERE id = :id"),
                {"full_name": full_name, "id": courier_id},
            )
            db.session.commit()


with app.app_context():
    _ensure_schema()


@app.get("/")
def index():
    return render_template("painel_gestao.html")


@app.get("/cliente")
def app_cliente():
    return render_template("app_cliente.html")


@app.get("/motoboy")
def app_motoboy():
    return render_template("app_motoboy.html")


@app.get("/api/establishments")
def list_establishments():
    rows = Establishment.query.order_by(Establishment.id.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@app.post("/api/establishments")
def create_establishment():
    data = request.get_json(silent=True) or {}
    store_name = (data.get("store_name") or data.get("name") or "").strip()
    if not store_name:
        return jsonify({"error": "Informe o nome do estabelecimento."}), 400
    est = Establishment(
        store_name=store_name,
        category=(data.get("category") or "Lanches & Refeições").strip(),
        default_delivery_fee=float(data.get("default_delivery_fee") or data.get("delivery_fee") or 8.0),
        estimated_time=(data.get("estimated_time") or "25-35 min").strip(),
    )
    db.session.add(est)
    db.session.commit()
    return jsonify(est.to_dict()), 201


@app.get("/api/products")
def list_products():
    rows = Product.query.order_by(Product.id.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@app.post("/api/products")
def create_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Informe o nome do produto."}), 400
    prod = Product(
        establishment_id=data.get("establishment_id"),
        name=name,
        description=(data.get("description") or "").strip(),
        price=float(data.get("price") or 0.0),
        featured=bool(data.get("featured", False)),
    )
    db.session.add(prod)
    db.session.commit()
    return jsonify(prod.to_dict()), 201


@app.get("/api/couriers")
def list_couriers():
    rows = Courier.query.order_by(Courier.id.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@app.post("/api/couriers")
def create_courier():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or data.get("name") or "").strip()
    phone = (data.get("phone") or data.get("whatsapp") or "").strip()
    cpf_clean = _digits(data.get("cpf") or "")
    vehicle = (data.get("vehicle") or "Moto").strip()
    plate = (data.get("plate") or "").strip().upper()
    status = (data.get("status") or "Offline").strip()

    if not full_name:
        return jsonify({"error": "Informe o nome do entregador."}), 400
    if len(_digits(phone)) < 8:
        return jsonify({"error": "Informe um telefone / WhatsApp válido."}), 400
    if cpf_clean and len(cpf_clean) not in (11, 14):
        return jsonify({"error": "CPF inválido."}), 400

    try:
        courier = Courier(
            full_name=full_name,
            phone=phone,
            cpf=cpf_clean or None,
            vehicle=vehicle,
            plate=plate,
            status=status,
        )
        db.session.add(courier)
        db.session.commit()
        _sync_legacy_courier_name(courier.id, full_name)
        return jsonify(courier.to_dict()), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": f"Erro ao salvar entregador: {exc}"}), 500


@app.get("/api/orders")
def list_orders():
    rows = Order.query.order_by(Order.id.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@app.post("/api/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    client_name = (data.get("client_name") or "").strip()
    client_phone = _digits(data.get("client_phone") or "")
    client_address = (data.get("client_address") or "").strip()

    if not client_name or len(client_phone) < 8 or not client_address:
        return jsonify({"error": "Preencha nome, celular e endereço."}), 400

    fee = float(data.get("delivery_fee") or 0.0)
    items_total = float(data.get("items_total") or 0.0)
    count = Order.query.count() + 1
    order = Order(
        order_code=f"RS-{count:03d}",
        store_id=data.get("store_id"),
        store_name=(data.get("store_name") or "Estabelecimento").strip(),
        client_name=client_name,
        client_phone=client_phone,
        client_address=client_address,
        items_total=items_total,
        delivery_fee=fee,
        courier_net_earning=round(fee, 2),
        status="Aguardando entregador",
    )
    db.session.add(order)
    db.session.commit()
    return jsonify(order.to_dict()), 201


@app.patch("/api/orders/<int:order_id>")
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json(silent=True) or {}

    if "courier_id" in data:
        order.courier_id = data["courier_id"]
    if "courier_accepted" in data:
        order.courier_accepted = bool(data["courier_accepted"])
    if "status" in data and str(data["status"]).strip():
        next_status = str(data["status"]).strip()
        if next_status.lower() == "entregue" and "delivery_code" in data:
            expected_code = _digits(order.client_phone)[-4:]
            provided_code = _digits(data.get("delivery_code"))
            if expected_code and provided_code != expected_code:
                return jsonify({"error": "Código de 4 dígitos incorreto."}), 400
        order.status = next_status

    db.session.commit()
    return jsonify(order.to_dict())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
