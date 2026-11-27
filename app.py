import re
from flask import jsonify, request


def _normalize_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


@app.post("/api/couriers")
def create_courier():
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or data.get("name") or "").strip()
    phone_raw = (data.get("phone") or data.get("whatsapp") or "").strip()
    phone_digits = _normalize_digits(phone_raw)
    cpf_digits = _normalize_digits(data.get("cpf") or "")
    vehicle = (data.get("vehicle") or "Moto").strip()
    plate = (data.get("plate") or "").strip().upper()
    status = (data.get("status") or "Offline").strip()

    if not full_name:
        return jsonify({"error": "Informe o nome do entregador."}), 400

    if len(phone_digits) < 8:
        return jsonify({"error": "Informe um telefone / WhatsApp válido."}), 400

    if cpf_digits and len(cpf_digits) not in (11, 14):
        return jsonify({"error": "CPF inválido."}), 400

    try:
        courier_kwargs = {
            "full_name": full_name,
            "phone": phone_raw,
            "vehicle": vehicle,
            "plate": plate,
            "status": status,
        }

        # Só inclui cpf se a coluna existir no modelo Courier
        if hasattr(Courier, "cpf"):
            courier_kwargs["cpf"] = cpf_digits or None

        courier = Courier(**courier_kwargs)
        db.session.add(courier)
        db.session.commit()

        payload = courier.to_dict() if hasattr(courier, "to_dict") else {
            "id": courier.id,
            "full_name": courier.full_name,
            "phone": courier.phone,
            "cpf": getattr(courier, "cpf", None),
            "vehicle": courier.vehicle,
            "plate": courier.plate,
            "status": courier.status,
        }
        return jsonify(payload), 201

    except Exception as exc:
        db.session.rollback()
        msg = str(exc)
        if "unique" in msg.lower() or "duplicate" in msg.lower():
            return jsonify({"error": "Já existe um entregador cadastrado com esse dado."}), 400
        return jsonify({"error": f"Erro ao salvar entregador: {msg}"}), 500
