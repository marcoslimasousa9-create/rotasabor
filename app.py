<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>RotaSabor — Pedidos Online</title>
  <meta name="theme-color" content="#0b1220" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <link rel="manifest" href="/static/manifest-cliente.json" />
  <link rel="icon" type="image/svg+xml" href="/static/icon.svg" />
  <style>
    :root {
      --bg: #070c16;
      --surface: #0f172a;
      --surface-2: #162033;
      --border: rgba(148, 163, 184, 0.16);
      --text: #f8fafc;
      --muted: #94a3b8;
      --primary: #38bdf8;
      --primary-dark: #0284c7;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
      --radius: 16px;
    }

    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding-bottom: 84px;
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 20;
      background: rgba(11, 18, 32, 0.92);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 14px 16px;
    }

    .topbar-row {
      max-width: 960px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .brand-logo {
      width: 38px;
      height: 38px;
      border-radius: 12px;
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      display: grid;
      place-items: center;
      font-weight: 900;
      font-size: 1.15rem;
      color: #04101d;
    }

    .brand-title { font-size: 1.05rem; font-weight: 800; line-height: 1.1; }
    .brand-sub { font-size: 0.76rem; color: var(--muted); }

    .badge-city {
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--primary);
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap;
    }

    .container {
      max-width: 960px;
      margin: 0 auto;
      padding: 16px;
    }

    .hero-banner {
      background: linear-gradient(135deg, rgba(2, 132, 199, 0.25), rgba(15, 23, 42, 0.95));
      border: 1px solid rgba(56, 189, 248, 0.28);
      border-radius: var(--radius);
      padding: 18px;
      margin-bottom: 16px;
    }

    .hero-banner h1 { margin: 0 0 6px; font-size: 1.25rem; }
    .hero-banner p { margin: 0; color: var(--muted); font-size: 0.9rem; }

    .search-box {
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 12px 14px;
      border-radius: 12px;
      font-size: 0.95rem;
      margin-bottom: 14px;
      outline: none;
    }

    .search-box:focus { border-color: var(--primary); }

    .chips-row {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 6px;
      margin-bottom: 14px;
      scrollbar-width: none;
    }

    .chips-row::-webkit-scrollbar { display: none; }

    .chip {
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--muted);
      padding: 8px 14px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 600;
      white-space: nowrap;
      cursor: pointer;
    }

    .chip.active {
      background: var(--primary);
      color: #04101d;
      border-color: var(--primary);
    }

    .section-title {
      font-size: 1rem;
      font-weight: 700;
      margin: 18px 0 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .grid-cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
      gap: 12px;
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 10px;
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
    }

    .card-title { font-weight: 700; font-size: 1rem; margin: 0; }
    .card-meta { color: var(--muted); font-size: 0.82rem; margin-top: 4px; }

    .tag {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 4px 8px;
      border-radius: 8px;
      background: rgba(56, 189, 248, 0.14);
      color: var(--primary);
      white-space: nowrap;
    }

    .card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      border-top: 1px solid var(--border);
      padding-top: 10px;
      font-size: 0.85rem;
    }

    .btn {
      border: none;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 700;
      font-size: 0.85rem;
      cursor: pointer;
    }

    .btn-primary {
      background: var(--primary);
      color: #04101d;
    }

    .btn-primary:hover { background: var(--primary-dark); color: #fff; }

    .btn-outline {
      background: var(--surface-2);
      color: var(--text);
      border: 1px solid var(--border);
    }

    .btn-block { width: 100%; padding: 13px; font-size: 0.95rem; }

    .qty-box {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--surface-2);
      border-radius: 10px;
      padding: 4px 8px;
    }

    .qty-btn {
      width: 26px;
      height: 26px;
      border-radius: 7px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      font-weight: 700;
      cursor: pointer;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }

    label {
      display: block;
      font-size: 0.8rem;
      color: var(--muted);
      margin-bottom: 5px;
      font-weight: 600;
    }

    input, select, textarea {
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 10px;
      font-size: 0.9rem;
      outline: none;
    }

    input:focus, select:focus, textarea:focus { border-color: var(--primary); }

    .status-pill {
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
      background: rgba(245, 158, 11, 0.16);
      color: var(--warning);
    }

    .status-pill.done {
      background: rgba(34, 197, 94, 0.16);
      color: var(--success);
    }

    .bottom-nav {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 30;
      background: rgba(11, 18, 32, 0.96);
      backdrop-filter: blur(12px);
      border-top: 1px solid var(--border);
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      padding: 6px 4px;
    }

    .nav-btn {
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 6px 4px;
      border-radius: 10px;
      font-size: 0.72rem;
      font-weight: 700;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 3px;
      cursor: pointer;
    }

    .nav-btn.active { color: var(--primary); }

    .toast {
      position: fixed;
      top: 72px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--surface-2);
      border: 1px solid var(--primary);
      color: var(--text);
      padding: 10px 16px;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: 600;
      z-index: 50;
      display: none;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.45);
    }

    .hidden { display: none !important; }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-row">
      <div class="brand">
        <div class="brand-logo">R</div>
        <div>
          <div class="brand-title">RotaSabor</div>
          <div class="brand-sub">App & Web do Cliente</div>
        </div>
      </div>
      <span class="badge-city" id="cityLabel">Catanduva - SP</span>
    </div>
  </header>

  <div class="toast" id="toastBox"></div>

  <main class="container">
    <!-- ABA 1: INÍCIO -->
    <section id="tab-home">
      <div class="hero-banner">
        <h1>Peça com rapidez na sua região</h1>
        <p>Escolha estabelecimentos, explore categorias e subcategorias e acompanhe sua entrega em tempo real.</p>
      </div>

      <input type="search" id="searchInput" class="search-box" placeholder="Buscar estabelecimento, lanche, marmita ou item..." />

      <div class="chips-row" id="quickFilters">
        <button class="chip active" data-filter="all">Todos</button>
        <button class="chip" data-filter="fast">Entrega rápida</button>
        <button class="chip" data-filter="lowfee">Menor taxa</button>
      </div>

      <div class="section-title">
        <span>Estabelecimentos disponíveis</span>
        <span class="card-meta" id="storesCount">0 lojas</span>
      </div>
      <div class="grid-cards" id="storesList"></div>
    </section>

    <!-- ABA 2: CATEGORIAS & SUBCATEGORIAS -->
    <section id="tab-catalog" class="hidden">
      <div class="section-title">
        <span>Categorias</span>
      </div>
      <div class="chips-row" id="categoryChips"></div>

      <div class="section-title">
        <span>Subcategorias</span>
      </div>
      <div class="chips-row" id="subcategoryChips"></div>

      <div class="section-title">
        <span id="catalogHeading">Itens em destaque</span>
      </div>
      <div class="grid-cards" id="catalogItems"></div>
    </section>

    <!-- ABA 3: SACOLA / CHECKOUT -->
    <section id="tab-cart" class="hidden">
      <div class="section-title">
        <span>Sua sacola</span>
        <button class="btn btn-outline" id="clearCartBtn" type="button">Limpar</button>
      </div>
      <div id="cartItemsContainer" class="grid-cards"></div>

      <div class="card" style="margin-top: 14px;">
        <div class="card-meta">Subtotal: <strong id="subtotalText">R$ 0,00</strong></div>
        <div class="card-meta">Taxa de entrega: <strong id="feeText">R$ 0,00</strong></div>
        <div class="card-title" style="margin-top: 4px;">Total: <span id="totalText" style="color: var(--primary);">R$ 0,00</span></div>
      </div>

      <form id="orderForm" class="card" style="margin-top: 14px;">
        <div class="card-title">Dados para entrega</div>
        <div class="form-grid">
          <div>
            <label for="clientName">Seu nome *</label>
            <input type="text" id="clientName" required placeholder="Ex.: Marcos Silva" />
          </div>
          <div>
            <label for="clientPhone">Telefone / WhatsApp</label>
            <input type="tel" id="clientPhone" placeholder="(17) 99999-9999" />
          </div>
          <div>
            <label for="clientNeighborhood">Bairro *</label>
            <input type="text" id="clientNeighborhood" required placeholder="Ex.: Centro" />
          </div>
          <div>
            <label for="paymentMethod">Pagamento</label>
            <select id="paymentMethod">
              <option value="Pix">Pix</option>
              <option value="Cartão na entrega">Cartão na entrega</option>
              <option value="Dinheiro">Dinheiro</option>
            </select>
          </div>
        </div>

        <div style="margin-bottom: 12px;">
          <label for="clientAddress">Endereço completo *</label>
          <input type="text" id="clientAddress" required placeholder="Rua, número, complemento e referência" />
        </div>

        <div style="margin-bottom: 14px;">
          <label for="orderNotes">Observações gerais do pedido</label>
          <textarea id="orderNotes" rows="2" placeholder="Ex.: Sem cebola, troco para R$ 50..."></textarea>
        </div>

        <button type="submit" class="btn btn-primary btn-block" id="submitOrderBtn">Finalizar Pedido</button>
      </form>
    </section>

    <!-- ABA 4: MEUS PEDIDOS -->
    <section id="tab-orders" class="hidden">
      <div class="section-title">
        <span>Meus pedidos</span>
        <button class="btn btn-outline" id="refreshOrdersBtn" type="button">Atualizar</button>
      </div>
      <div id="ordersList" class="grid-cards"></div>
    </section>
  </main>

  <nav class="bottom-nav">
    <button class="nav-btn active" data-tab="tab-home" type="button">
      <span>Início</span>
    </button>
    <button class="nav-btn" data-tab="tab-catalog" type="button">
      <span>Categorias</span>
    </button>
    <button class="nav-btn" data-tab="tab-cart" type="button">
      <span>Sacola (<span id="cartBadge">0</span>)</span>
    </button>
    <button class="nav-btn" data-tab="tab-orders" type="button">
      <span>Pedidos</span>
    </button>
  </nav>

  <script>
    const CATALOG_STRUCTURE = {
      "Lanches & Pizzas": {
        subcategories: ["Smash & Burgers", "Combos", "Pizzas & Esfihas"],
        items: [
          { id: "b1", name: "Duplo Smash Bacon", category: "Lanches & Pizzas", subcategory: "Smash & Burgers", price: 28.0, desc: "Dois blends 100g, cheddar, bacon crocante e molho da casa." },
          { id: "b2", name: "Combo Burger + Batata + Refri", category: "Lanches & Pizzas", subcategory: "Combos", price: 39.9, desc: "Lanche artesanal, porção de batata frita e bebida lata." },
          { id: "p1", name: "Pizza Média Calabresa", category: "Lanches & Pizzas", subcategory: "Pizzas & Esfihas", price: 44.0, desc: "Massa leve, muçarela, calabresa fatiada e orégano." }
        ]
      },
      "Refeições & Marmitas": {
        subcategories: ["Marmitas Executivas", "Pratos Caseiros", "Fit & Saudável"],
        items: [
          { id: "m1", name: "Marmita Frango Grelhado", category: "Refeições & Marmitas", subcategory: "Marmitas Executivas", price: 22.0, desc: "Arroz, feijão, filé de frango grelhado, purê e salada." },
          { id: "m2", name: "Prato Caseiro Contra-Filé", category: "Refeições & Marmitas", subcategory: "Pratos Caseiros", price: 27.5, desc: "Contra-filé acebolado, arroz soltinho, feijão e farofa." },
          { id: "m3", name: "Marmita Fit Frango & Batata Doce", category: "Refeições & Marmitas", subcategory: "Fit & Saudável", price: 24.0, desc: "Frango desfiado temperado, batata doce e brócolis." }
        ]
      },
      "Açaí & Sobremesas": {
        subcategories: ["Copos & Tigelas", "Adicionais", "Doces Gelados"],
        items: [
          { id: "a1", name: "Açaí na Tigela 500ml", category: "Açaí & Sobremesas", subcategory: "Copos & Tigelas", price: 21.0, desc: "Açaí cremoso batido na hora com banana e granola." },
          { id: "a2", name: "Extra Leite Ninho & Morango", category: "Açaí & Sobremesas", subcategory: "Adicionais", price: 6.5, desc: "Cobertura caprichada de leite em pó e morangos frescos." }
        ]
      },
      "Bebidas & Conveniência": {
        subcategories: ["Refrigerantes & Sucos", "Águas & Energéticos", "Itens Rápidos"],
        items: [
          { id: "d1", name: "Refrigerante 2L", category: "Bebidas & Conveniência", subcategory: "Refrigerantes & Sucos", price: 13.0, desc: "Garrafa 2 litros bem gelada." },
          { id: "d2", name: "Água Mineral sem Gás 500ml", category: "Bebidas & Conveniência", subcategory: "Águas & Energéticos", price: 4.0, desc: "Garrafa 500ml gelada." }
        ]
      }
    };

    let stores = [];
    let selectedStoreId = null;
    let activeCategory = Object.keys(CATALOG_STRUCTURE)[0];
    let activeSubcategory = CATALOG_STRUCTURE[activeCategory].subcategories[0];
    let quickFilter = "all";
    let searchTerm = "";
    let cart = JSON.parse(localStorage.getItem("rotasabor_cart") || "[]");

    const fmtBRL = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

    function showToast(msg) {
      const box = document.getElementById("toastBox");
      box.textContent = msg;
      box.style.display = "block";
      clearTimeout(window._toastTimer);
      window._toastTimer = setTimeout(() => { box.style.display = "none"; }, 2600);
    }

    function saveCart() {
      localStorage.setItem("rotasabor_cart", JSON.stringify(cart));
      updateCartBadge();
    }

    function updateCartBadge() {
      const totalQty = cart.reduce((acc, item) => acc + item.qty, 0);
      document.getElementById("cartBadge").textContent = totalQty;
    }

    function switchTab(tabId) {
      document.querySelectorAll("main > section").forEach((sec) => sec.classList.add("hidden"));
      document.getElementById(tabId).classList.remove("hidden");
      document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.tab === tabId);
      });
      if (tabId === "tab-cart") renderCart();
      if (tabId === "tab-orders") loadOrders();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    async function loadStores() {
      try {
        const res = await fetch("/api/stores");
        if (res.ok) {
          stores = await res.json();
        }
      } catch (_) {}

      if (!stores.length) {
        stores = [
          { id: 1, name: "Hamburgueria Centro", category: "Lanches & Pizzas", city: "Catanduva - SP", delivery_fee: 8.0, prep_time: "25-35 min", active: true },
          { id: 2, name: "Marmitaria Sabor da Casa", category: "Refeições & Marmitas", city: "Catanduva - SP", delivery_fee: 7.0, prep_time: "30-45 min", active: true }
        ];
      }
      if (!selectedStoreId && stores[0]) {
        selectedStoreId = stores[0].id;
        document.getElementById("cityLabel").textContent = stores[0].city || "Catanduva - SP";
      }
      renderStores();
    }

    function renderStores() {
      const q = searchTerm.toLowerCase().trim();
      let list = stores.filter((s) => s.active !== false);

      if (q) {
        list = list.filter((s) =>
          (s.name || "").toLowerCase().includes(q) ||
          (s.category || "").toLowerCase().includes(q) ||
          (s.city
