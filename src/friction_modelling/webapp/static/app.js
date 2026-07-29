/* Friction-modelling frontend — talks to the FastAPI backend in api.py. */
"use strict";

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, txt) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt != null) n.textContent = txt;
  return n;
};

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { const j = await res.json(); if (j.detail) msg = j.detail; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

/* ------------------------------------------------------------------ */
/* Tab switching                                                       */
/* ------------------------------------------------------------------ */
function showTab(name) {
  document.querySelectorAll(".tab").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) =>
    p.classList.toggle("active", p.id === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => showTab(btn.dataset.tab));
});

// Hero call-to-action buttons ("Run the pipeline" / "Read the methodology").
document.querySelectorAll("[data-goto]").forEach((btn) => {
  btn.addEventListener("click", () => showTab(btn.dataset.goto));
});

/* ------------------------------------------------------------------ */
/* Overview / status                                                   */
/* ------------------------------------------------------------------ */
let STATE = null;
const MODEL_LABELS = {
  physics: "Coulomb-Viscous (physics)",
  nn: "Black-box neural network",
  pinn: "LuGre PINN",
};

function boolCell(ok) {
  const td = el("td", ok ? "ok" : "bad", ok ? "✓" : "—");
  return td;
}

async function loadStatus() {
  const meta = $("#meta");
  try {
    STATE = await api("/api/status");
  } catch (err) {
    meta.innerHTML = "";
    meta.appendChild(el("span", "pill bad", "backend offline"));
    return;
  }

  // top-bar pills
  meta.innerHTML = "";
  meta.appendChild(el("span", "pill", `v${STATE.version}`));
  meta.appendChild(el("span", "pill", `N=${STATE.gear_ratio}`));
  meta.appendChild(el("span", "pill", `${STATE.sample_rate_hz} Hz`));
  meta.appendChild(el("span", STATE.data_ready ? "pill ok" : "pill bad",
    STATE.data_ready ? "data ready" : "data missing"));

  renderHeroStats();
  renderStatusCards();
  renderStatusTable();
  $("#footer-version").textContent =
    `friction-modelling v${STATE.version} · data: ${STATE.data_root}`;
}

function renderHeroStats() {
  const wrap = $("#hero-stats");
  if (!wrap) return;
  wrap.innerHTML = "";
  const nJoints = STATE.joints.length;
  const nReady = STATE.joints.filter((j) => j.velocity).length;
  const trained = Object.values(STATE.results).filter((v) => v === true).length;
  const stats = [
    [nJoints, "Joints modelled"],
    ["3", "Friction models"],
    [`${nReady}/${nJoints}`, "Preprocessed"],
    [`${trained}/3`, "Models trained"],
  ];
  for (const [n, l] of stats) {
    const s = el("div", "hstat");
    s.appendChild(el("div", "n", String(n)));
    s.appendChild(el("div", "l", l));
    wrap.appendChild(s);
  }
}

function renderStatusCards() {
  const wrap = $("#status-cards");
  wrap.innerHTML = "";
  const nJoints = STATE.joints.length;
  const nReady = STATE.joints.filter((j) => j.velocity).length;
  const trained = Object.entries(STATE.results)
    .filter(([, v]) => v === true).length;

  const cards = [
    ["Joints modelled", STATE.joints.map((j) => "J" + j.joint).join(", "), false],
    ["Preprocessed", `${nReady} / ${nJoints}`, false],
    ["Models with results", `${trained} / 3`, false],
    ["Gear ratio", "N = " + STATE.gear_ratio, false],
  ];
  for (const [k, v, small] of cards) {
    const c = el("div", "card");
    c.appendChild(el("div", "k", k));
    c.appendChild(el("div", "v" + (small ? " small" : ""), v));
    wrap.appendChild(c);
  }
}

function renderStatusTable() {
  const t = $("#status-table");
  t.innerHTML = "";
  const head = el("tr");
  ["Joint", "Raw", "Cleaned", "Velocity", "Acceleration"].forEach((h) =>
    head.appendChild(el("th", null, h)));
  const thead = el("thead"); thead.appendChild(head); t.appendChild(thead);

  const tb = el("tbody");
  for (const j of STATE.joints) {
    const tr = el("tr");
    tr.appendChild(el("td", null, "J" + j.joint));
    tr.appendChild(boolCell(j.raw));
    tr.appendChild(boolCell(j.clean));
    tr.appendChild(boolCell(j.velocity));
    tr.appendChild(boolCell(j.acceleration));
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}

/* ------------------------------------------------------------------ */
/* Data explorer                                                       */
/* ------------------------------------------------------------------ */
function populateJointSelect() {
  const sel = $("#data-joint");
  sel.innerHTML = "";
  for (const j of STATE.joints) {
    const o = el("option", null, "Joint " + j.joint);
    o.value = j.joint;
    sel.appendChild(o);
  }
}

function renderTable(tableEl, columns, rows) {
  tableEl.innerHTML = "";
  const thead = el("thead");
  const hr = el("tr");
  columns.forEach((c) => hr.appendChild(el("th", null, c)));
  thead.appendChild(hr);
  tableEl.appendChild(thead);

  const tb = el("tbody");
  for (const row of rows) {
    const tr = el("tr");
    columns.forEach((c) => {
      let v = row[c];
      if (typeof v === "number") v = Number.isInteger(v) ? v : v.toFixed(6);
      tr.appendChild(el("td", null, v == null ? "" : String(v)));
    });
    tb.appendChild(tr);
  }
  tableEl.appendChild(tb);
}

async function loadData() {
  const joint = $("#data-joint").value;
  const btn = $("#load-data");
  btn.disabled = true;
  const stamp = Date.now();  // cache-bust the plot images
  $("#plot-raw").src = `/api/data/${joint}/raw-plot?t=${stamp}`;
  $("#plot-friction").src = `/api/data/${joint}/friction-plot?t=${stamp}`;
  try {
    const d = await api(`/api/data/${joint}/table?rows=100`);
    renderTable($("#data-table"), d.columns, d.rows);
  } catch (err) {
    renderTable($("#data-table"), ["error"], [{ error: err.message }]);
  } finally {
    btn.disabled = false;
  }
}

/* ------------------------------------------------------------------ */
/* Run models                                                          */
/* ------------------------------------------------------------------ */
const RUN_ORDER = [
  ["preprocess", "Preprocess pipeline", "Clean → velocity → acceleration for all joints."],
  ["physics", "Coulomb-Viscous", "Least-squares fit of the analytical friction model."],
  ["nn", "Neural network", "Train the black-box MLP per joint (slow)."],
  ["pinn", "LuGre PINN", "Physics-informed network with steady-state loss (slow)."],
];

function renderModelGrid() {
  const grid = $("#model-grid");
  grid.innerHTML = "";
  for (const [key, title, desc] of RUN_ORDER) {
    const card = el("div", "model-card");
    card.appendChild(el("h4", null, title));
    card.appendChild(el("p", "desc", desc));
    const state = el("div", "state", "idle");
    state.id = `state-${key}`;
    const btn = el("button", "btn", "Run");
    btn.addEventListener("click", () => runModel(key, btn, state));
    card.appendChild(btn);
    card.appendChild(state);
    grid.appendChild(card);
  }
}

async function runModel(key, btn, state) {
  const log = $("#run-log");
  btn.disabled = true;
  state.className = "state running";
  state.innerHTML = '<span class="spinner"></span> starting…';
  log.textContent = `▶ ${key}: submitting…\n`;
  try {
    const { job_id } = await api(`/api/run/${key}`, { method: "POST" });
    await pollJob(job_id, key, btn, state);
  } catch (err) {
    state.className = "state error";
    state.textContent = "error";
    log.textContent += `✖ ${err.message}\n`;
    btn.disabled = false;
  }
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function pollJob(jobId, key, btn, state) {
  const log = $("#run-log");
  while (true) {
    await sleep(1500);
    let job;
    try {
      job = await api(`/api/job/${jobId}`);
    } catch (err) {
      state.className = "state error";
      state.textContent = "lost job";
      log.textContent += `✖ ${err.message}\n`;
      break;
    }
    if (job.status === "running") {
      state.innerHTML = '<span class="spinner"></span> running…';
      continue;
    }
    if (job.status === "done") {
      state.className = "state done";
      state.textContent = "done ✓";
      log.textContent += (job.log || "") + `\n✔ ${key} finished.\n`;
      await loadStatus();  // refresh readiness / results flags
    } else {
      state.className = "state error";
      state.textContent = "error";
      log.textContent += (job.log || "") + `\n✖ ${job.error || "failed"}\n`;
    }
    break;
  }
  log.scrollTop = log.scrollHeight;
  btn.disabled = false;
}

/* ------------------------------------------------------------------ */
/* Results                                                             */
/* ------------------------------------------------------------------ */
async function loadResults() {
  const model = $("#result-model").value;
  const btn = $("#load-results");
  btn.disabled = true;
  try {
    const d = await api(`/api/results/${model}`);
    renderTable($("#results-table"), d.columns, d.rows);
  } catch (err) {
    renderTable($("#results-table"), ["message"], [{ message: err.message }]);
  } finally {
    btn.disabled = false;
  }
}

/* ------------------------------------------------------------------ */
/* Init                                                                */
/* ------------------------------------------------------------------ */
async function init() {
  await loadStatus();
  if (STATE) {
    populateJointSelect();
    renderModelGrid();
  }
  $("#load-data").addEventListener("click", loadData);
  $("#load-results").addEventListener("click", loadResults);
}

init();
