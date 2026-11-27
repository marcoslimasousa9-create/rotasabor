
"""Aplica as alterações das telas (templates/*.html) para o novo app.py.

Uso (na pasta do repositório, onde fica a pasta templates):  python patch_frontend.py
Rode UMA vez. Se algum trecho não for encontrado, o arquivo correspondente NÃO é alterado.
"""
import pathlib
import sys

PRODUCTS_SECTION = r'''<section id="sec-products" class="grid-2 hidden">
      <div class="card">
        <h2>Cadastrar Produto</h2>
        <div class="muted">Itens que aparecem no app do cliente.</div>
        <form id="productForm">
          <label for="prodStore">Estabelecimento</label>
          <select id="prodStore" required></select>
          <label for="prodName">Nome do produto</label>
          <input type="text" id="prodName" required />
          <label for="prodPrice">Preço (R$)</label>
          <input type="number" step="0.01" min="0.5" id="prodPrice" required />
          <label for="prodDesc">Descrição</label>
          <input type="text" id="prodDesc" />
          <div class="submit-wrap">
            <button class="btn btn-success" type="submit">Salvar Produto</button>
          </div>
        </form>
      </div>
      <div class="card">
        <h2>Produtos Cadastrados</h2>
        <div class="muted">Só estes itens podem ser pedidos pelos clientes.</div>
        <div id="productsList">Carregando...</div>
      </div>
    </section>'''

PRODUCTS_JS = r'''async function loadProducts() {
      const [pr, sr] = await Promise.all([fetch("/api/products"), fetch("/api/establishments")]);
      const prods = pr.ok ? await pr.json() : [];
      const stores = sr.ok ? await sr.json() : [];
      document.getElementById("prodStore").innerHTML = stores.map((s) => `<option value="${s.id}">${s.store_name}</option>`).join("");
      const names = Object.fromEntries(stores.map((s) => [s.id, s.store_name]));
      document.getElementById("productsList").innerHTML = prods.map((p) => `
        <div class="item-row">
          <strong>${p.name}</strong> • ${fmtBRL(p.price)}
          <div class="muted" style="margin:4px 0 0;">${names[p.establishment_id] || "Sem loja"}${p.description ? " • " + p.description : ""}</div>
        </div>
      `).join("") || `<div class="muted">Nenhum produto cadastrado ainda.</div>`;
    }

    document.getElementById("productForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const res = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          establishment_id: Number(document.getElementById("prodStore").value),
          name: document.getElementById("prodName").value.trim(),
          price: document.getElementById("prodPrice").value,
          description: document.getElementById("prodDesc").value.trim()
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { alert(data.error || "Erro ao salvar produto."); return; }
      e.target.reset();
      loadProducts();
    });'''

CLIENTE = [
    ("let storesData = [...SEED_STORES];", "let storesData = [];"),
    (": seedFallback.items;", ": [];"),
    ('rating: "4.9",', 'rating: "Novo",'),
    ('reviews: "100+",', 'reviews: "sem avaliações",'),
    ("items_total: itemsTotal,", '''payment_method: document.getElementById("cliPayment").value,
            items: cart.map((x) => ({ id: x.id, qty: x.qty })),'''),
    ('toast(`Pedido ${data.order_code || ""} enviado!`);', '''try {
          const tk = JSON.parse(localStorage.getItem("rotasabor_tokens") || "[]");
          tk.unshift(data.tracking_token);
          localStorage.setItem("rotasabor_tokens", JSON.stringify(tk.slice(0, 20)));
        } catch (_) {}
        toast(`Pedido ${data.order_code || ""} enviado! Código de entrega: ${data.delivery_code}`);'''),
    ('const res = await fetchWithTimeout("/api/orders");', '''const tokens = JSON.parse(localStorage.getItem("rotasabor_tokens") || "[]");
        if (!tokens.length) { box.innerHTML = `<div class="muted-txt">Nenhum pedido recente.</div>`; return; }
        const res = await fetchWithTimeout("/api/orders/track?tokens=" + encodeURIComponent(tokens.join(",")));'''),
    ('const list = phoneFilter ? rows.filter((r) => String(r.client_phone || "").includes(phoneFilter)) : rows.slice(0, 5);',
     "const list = rows;"),
    ('<div class="muted-txt" style="margin-top:5px;">${o.client_address || ""}</div>',
     '''<div class="muted-txt" style="margin-top:5px;">${o.client_address || ""}</div>
            ${o.status !== "Entregue" && o.delivery_code ? `<div style="font-size:19px;font-weight:900;margin-top:6px;">Código de entrega: ${o.delivery_code}</div>` : ""}'''),
    ("Celular (4 últimos dígitos confirmam na entrega)", "Celular / WhatsApp (com DDD)"),
    ('<option value="Pix">Pix</option>', ""),
]

MOTOBOY = [
    ("let map = null;", '''fetch("/api/me").then((r) => r.json()).then((m) => { if (m.role !== "courier") location.href = "/login"; }).catch(() => {});
    let map = null;'''),
    ("Peça os 4 últimos números do celular do cliente.", "Peça ao cliente o código de 4 dígitos que aparece no app dele."),
    ("Digite os 4 últimos números do celular.", "Digite o código de 4 dígitos do cliente."),
    ('toast("Digite os 4 últimos números");', 'toast("Digite o código de 4 dígitos");'),
    ("stepState[order.id] = nextStage;", '''stepState[order.id] = nextStage;
      if (nextStage === "to_client") {
        fetch(`/api/orders/${order.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "Em rota" }) }).catch(() => {});
      }'''),
    ('''<button class="menu-row" type="button" onclick="toast('Suporte RotaSabor — Catanduva/SP')">''',
     '''<button class="menu-row" type="button" onclick="fetch('/api/logout', { method: 'POST' }).then(() => { location.href = '/login'; })">
      <span>Sair</span>
      <span>›</span>
    </button>

    <button class="menu-row" type="button" onclick="toast('Suporte RotaSabor — Catanduva/SP')">'''),
]

PAINEL = [
    ('["sec-clients", "sec-stores", "sec-couriers", "sec-orders"].forEach((id) => {',
     '["sec-clients", "sec-stores", "sec-couriers", "sec-products", "sec-orders"].forEach((id) => {'),
    ('<button class="tab-btn" data-section="sec-orders" type="button">4. Entregas</button>',
     '''<button class="tab-btn" data-section="sec-orders" type="button">4. Entregas</button>
      <button class="tab-btn" data-section="sec-products" type="button">5. Produtos</button>'''),
    ('<section id="sec-orders" class="card hidden">', PRODUCTS_SECTION + '\n\n    <section id="sec-orders" class="card hidden">'),
    ('alert("Entregador salvo com sucesso!");',
     'alert("Entregador salvo! Login: o telefone dele. Senha de acesso (anote, aparece só agora): " + data.initial_password);'),
    ('<button class="btn btn-primary" type="button" id="refreshAllBtn">Atualizar Tudo</button>',
     '''<button class="btn" type="button" onclick="fetch('/api/logout', { method: 'POST' }).then(() => { location.href = '/login'; })">Sair</button>
        <button class="btn btn-primary" type="button" id="refreshAllBtn">Atualizar Tudo</button>'''),
    ("function refreshAll() {", PRODUCTS_JS + "\n\n    function refreshAll() {\n      loadProducts();"),
]

FILES = {"app_cliente.html": CLIENTE, "app_motoboy.html": MOTOBOY, "painel_gestao.html": PAINEL}


def patch(folder="templates"):
    ok = True
    for name, pairs in FILES.items():
        path = pathlib.Path(folder) / name
        if not path.exists():
            print(f"[ERRO] {path} não existe. Rode na pasta do repositório.")
            ok = False
            continue
        text = path.read_text(encoding="utf-8")
        missing = [old[:70] for old, _ in pairs if old not in text]
        if missing:
            print(f"[ERRO] {name}: não alterado. Trechos não encontrados:")
            for m in missing:
                print("   -", m)
            ok = False
            continue
        for old, new in pairs:
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print(f"[ok] {name}: {len(pairs)} alterações aplicadas")
    return ok


if __name__ == "__main__":
    sys.exit(0 if patch() else 1)
