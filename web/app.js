"use strict";

let CATALOG = null;
let SPECS = {};
let MODE = "historico"; // "historico" | "atual"
let CHART = null;

const BRL = (n) =>
  n == null ? "—" : n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const USD = (n) =>
  n == null ? "—" : "US$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2 });

const slug = (modelo) =>
  "iphone-" +
  modelo.replace(/iPhone\s*/i, "").trim().toLowerCase().replace(/\s+/g, "-");

const fmtData = (iso) => {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    const resp = await fetch("catalog.json", { cache: "no-store" });
    CATALOG = await resp.json();
  } catch (e) {
    document.querySelector("main").innerHTML =
      '<p style="color:#f87272">Falha ao carregar catalog.json.</p>';
    return;
  }
  try {
    SPECS = await (await fetch("specs.json", { cache: "no-store" })).json();
  } catch (e) {
    SPECS = {}; // resiliente: cards funcionam sem ficha técnica
  }
  document.getElementById("fornecedor").textContent =
    CATALOG.cotacoes[0]?.fornecedor ?? "—";
  document.getElementById("data-fonte").textContent = CATALOG.cotacoes
    .map((c) => c.data)
    .join(" · ");

  bindToggle();
  bindSearch();
  buildChartSelector();
  renderAll();
}

function renderAll() {
  renderKpis();
  renderAlerts();
  renderGrid(document.getElementById("search").value);
  renderChart(document.getElementById("chart-model").value);
}

function bindToggle() {
  const hint = document.getElementById("mode-hint");
  document.querySelectorAll(".toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".toggle button").forEach((b) =>
        b.classList.remove("active")
      );
      btn.classList.add("active");
      MODE = btn.dataset.mode;
      hint.textContent =
        MODE === "historico"
          ? "Preços convertidos com o dólar de cada data. Base confiável para comparar."
          : "Simulação com o câmbio atual (API). Não use para comparar tendência.";
      renderGrid(document.getElementById("search").value);
    });
  });
}

function bindSearch() {
  document
    .getElementById("search")
    .addEventListener("input", (e) => renderGrid(e.target.value));
}

function renderKpis() {
  const prods = CATALOG.produtos;
  const atual = CATALOG.meta.exchange_rate_brl_current;
  const baratos = prods
    .filter((p) => p.preco_brl_historico != null)
    .sort((a, b) => a.preco_brl_historico - b.preco_brl_historico);
  const quedas = CATALOG.insights.filter((i) => i.tipo === "queda_real").length;
  const melhorDia = CATALOG.ranking?.melhor_dia;
  const slotDia = melhorDia ? CATALOG.ranking.por_data[melhorDia] : null;

  const kpis = [
    { label: "Produtos", value: prods.length, foot: `${CATALOG.cotacoes.length} coletas` },
    {
      label: "Melhor dia pra comprar",
      value: melhorDia ? fmtData(melhorDia) : "—",
      foot: slotDia ? `${slotDia.n_menores} menores preços` : "base histórica",
    },
    {
      label: "Mais barato (hist.)",
      value: BRL(baratos[0]?.preco_brl_historico),
      foot: baratos[0]?.modelo_normalizado ?? "—",
    },
    { label: "Quedas reais (USD)", value: quedas, foot: "boas janelas de compra" },
    {
      label: "Dólar atual",
      value: atual ? "R$ " + atual.toFixed(2) : "—",
      foot: atual ? "via API" : "rode sem --no-api",
    },
  ];
  document.getElementById("kpis").innerHTML = kpis
    .map(
      (k) => `<div class="kpi"><div class="label">${k.label}</div>
      <div class="value">${k.value}</div><div class="foot">${k.foot}</div></div>`
    )
    .join("");
}

function renderAlerts() {
  const alertas = CATALOG.insights.filter(
    (i) => i.tipo === "queda_real" || i.tipo === "queda_falsa"
  );
  if (!alertas.length) {
    document.getElementById("alerts").innerHTML = "";
    return;
  }
  document.getElementById("alerts").innerHTML = alertas
    .slice(0, 6)
    .map((a) => {
      const cls = a.tipo === "queda_real" ? "real" : "falsa";
      const tag = a.tipo === "queda_real" ? "Queda real" : "Queda falsa";
      return `<div class="alert ${cls}"><span class="tag">${tag}</span>
        <p>${a.mensagem}</p></div>`;
    })
    .join("");
}

function renderGrid(filtro = "") {
  const q = filtro.trim().toLowerCase();
  const prods = CATALOG.produtos.filter((p) =>
    p.modelo_normalizado.toLowerCase().includes(q)
  );
  document.getElementById("grid").innerHTML = prods.map(cardHTML).join("");
}

function cardHTML(p) {
  const usePreco = MODE === "historico" ? p.preco_brl_historico : p.preco_brl_atual;
  const precoLabel = MODE === "historico" ? "BRL histórico" : "BRL atual (sim.)";
  const rowCls = MODE === "historico" ? "" : "sim";
  const cores = p.cores
    .map((c) => `<span class="badge color">${c}</span>`)
    .join("");
  const tipo = p.tipo ? `<span class="badge">${p.tipo}</span>` : "";
  const img = slug(p.modelo_normalizado);
  return `<article class="card">
    <div class="thumb">
      <img src="images/${img}.png" alt="${p.modelo_normalizado}"
        onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ph',textContent:'📱'}))" />
    </div>
    <h3>${p.modelo_normalizado}</h3>
    <div class="meta">${p.armazenamento} · ${p.data}</div>
    <div class="badges">${tipo}${cores}</div>
    <div class="prices">
      <div class="price-row usd"><span class="k">USD</span><span class="v">${USD(p.preco_usd)}</span></div>
      <div class="price-row ${rowCls}"><span class="k">${precoLabel}</span><span class="v">${BRL(usePreco)}</span></div>
    </div>
    ${melhorPrecoBadge(p)}
    ${p.observacoes ? `<div class="obs">⚑ ${p.observacoes}</div>` : ""}
    ${fichaHTML(p.modelo_normalizado)}
  </article>`;
}

function melhorPrecoBadge(p) {
  const chave = `${p.modelo_normalizado}|${p.armazenamento}|${p.tipo}`;
  const g = CATALOG.analise[chave];
  if (!g || g.menor_preco_brl_historico == null) return "";
  return `<div class="best">⬇ menor preço: <strong>${BRL(
    g.menor_preco_brl_historico
  )}</strong> em ${fmtData(g.menor_preco_data)}</div>`;
}

function fichaHTML(modelo) {
  const s = SPECS[modelo];
  if (!s) return "";
  const linhas = [
    ["Tela", s.tela], ["Chip", s.chip], ["RAM", s.ram], ["Bateria", s.bateria],
    ["Câmeras", s.cameras], ["Dimensões", s.dimensoes], ["Peso", s.peso],
    ["SO", s.so], ["Conexões", s.conectividade], ["Ano", s.ano],
  ]
    .filter(([, v]) => v != null && v !== "")
    .map(([k, v]) => `<div class="srow"><span>${k}</span><span>${v}</span></div>`)
    .join("");
  if (!linhas) return "";
  return `<details class="ficha"><summary>Ver ficha técnica</summary>
    <div class="specs">${linhas}</div></details>`;
}

function buildChartSelector() {
  const sel = document.getElementById("chart-model");
  const chaves = Object.keys(CATALOG.analise).sort();
  sel.innerHTML = chaves
    .map((k) => {
      const g = CATALOG.analise[k];
      return `<option value="${k}">${g.modelo_normalizado} ${g.armazenamento} ${g.tipo}</option>`;
    })
    .join("");
  sel.addEventListener("change", (e) => renderChart(e.target.value));
}

function renderChart(chave) {
  const g = CATALOG.analise[chave];
  if (!g) return;
  const precos = g.precos_brl_historico;
  const minVal = Math.min(...precos);
  const ptColors = precos.map((v) => (v === minVal ? "#36d399" : "#5b8cff"));
  const ptRadii = precos.map((v) => (v === minVal ? 8 : 5));
  const ctx = document.getElementById("trend-chart");
  if (CHART) CHART.destroy();
  CHART = new Chart(ctx, {
    type: "line",
    data: {
      labels: g.datas,
      datasets: [
        {
          label: "BRL histórico (● verde = menor)",
          data: precos,
          borderColor: "#5b8cff",
          backgroundColor: "rgba(91,140,255,.15)",
          fill: true,
          tension: 0.3,
          pointRadius: ptRadii,
          pointBackgroundColor: ptColors,
          pointBorderColor: ptColors,
        },
      ],
    },
    options: {
      plugins: { legend: { labels: { color: "#93a0b8" } } },
      scales: {
        x: { ticks: { color: "#93a0b8" }, grid: { color: "#232c40" } },
        y: { ticks: { color: "#93a0b8" }, grid: { color: "#232c40" } },
      },
    },
  });
}
