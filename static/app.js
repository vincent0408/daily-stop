// Daily Stop front end. Loads each source in parallel so sections appear as they arrive.
const MIN_CARD = 270, GAP = 14;  // keep in sync with .grid in style.css

// How many cards to show before "Show more", so the last row is always full.
function initialCount() {
  const width = $("main").clientWidth - 2 * parseFloat(getComputedStyle($("main")).paddingLeft);
  const cols = Math.max(1, Math.floor((width + GAP) / (MIN_CARD + GAP)));
  if (cols === 1) return 5;
  const leadSpans = window.innerWidth >= 900 ? 2 : 1;  // matches the .card.lead media query
  return cols * 2 - (leadSpans - 1);
}

const state = {
  mode: "server",       // "server" (uvicorn) or "static" (GitHub Pages)
  site: null,           // static mode: feed.json metadata (repo, workflow, generated_at)
  sources: [],          // [{id, name, color, ...}]
  feeds: new Map(),     // id -> SourceFeed
  expanded: new Set(),  // ids showing all cards
  filter: "all",
};

const $ = (sel) => document.querySelector(sel);
const el = (tag, props = {}, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((c) => c != null));
  return node;
};

function timeAgo(iso) {
  if (!iso) return "";
  const mins = Math.round((Date.now() - new Date(iso)) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  return hrs < 24 ? `${hrs} h ago` : new Date(iso).toLocaleDateString();
}

/* ---------- Masthead ---------- */
function renderMasthead() {
  const now = new Date();
  $("#weekday").textContent = now.toLocaleDateString(undefined, { weekday: "long" });
  $("#date").textContent = now.toLocaleDateString(undefined, { month: "long", day: "numeric" });
}

function renderSummary() {
  const loaded = [...state.feeds.values()];
  const total = loaded.reduce((n, f) => n + f.items.length, 0);
  const spectrum = $("#spectrum");
  spectrum.replaceChildren(
    ...state.sources.map((s) => {
      const n = state.feeds.get(s.id)?.items.length ?? 0;
      return el("span", { style: `background:${s.color};flex-grow:${n}` });
    })
  );
  const pending = state.sources.length - loaded.length;
  const ok = loaded.filter((f) => f.items.length).length;
  const all = state.sources.length;
  $("#summary").textContent = pending
    ? `Loading ${pending} of ${all} sources…`
    : `${total} picks from ${ok === all ? `${all} sources` : `${ok} of ${all} sources`}` +
      (state.site?.generated_at ? `, updated ${timeAgo(state.site.generated_at)}` : "");
}

/* ---------- Filters ---------- */
function renderFilters() {
  const chip = (id, label, color, count) => {
    const b = el("button", { type: "button", className: "chip" },
      color ? el("span", { className: "dot" }) : null,
      el("span", { textContent: label }),
      count != null ? el("span", { className: "count", textContent: count }) : null);
    if (color) b.style.setProperty("--c", color);
    b.setAttribute("aria-pressed", String(state.filter === id));
    b.addEventListener("click", () => { state.filter = id; renderFilters(); applyFilter(); });
    return b;
  };
  $("#filters").replaceChildren(
    chip("all", "All"),
    ...state.sources.map((s) => chip(s.id, s.name, s.color, state.feeds.get(s.id)?.items.length))
  );
}

function applyFilter() {
  document.querySelectorAll(".source").forEach((sec) => {
    sec.hidden = state.filter !== "all" && sec.dataset.id !== state.filter;
  });
}

/* ---------- Sections ---------- */
function sectionShell(source) {
  const sec = el("section", { className: "source" });
  sec.dataset.id = source.id;
  sec.style.setProperty("--c", source.color);
  sec.setAttribute("aria-labelledby", `h-${source.id}`);
  return sec;
}

function sectionHead(source, feed) {
  const meta = el("div", { className: "source-meta" });
  if (feed?.stale) meta.append(el("span", { className: "stale-note", textContent: "Showing earlier results" }));
  if (feed?.fetched_at) meta.append(el("span", { textContent: `Updated ${timeAgo(feed.fetched_at)}` }));
  meta.append(el("a", { href: source.homepage, target: "_blank", rel: "noopener noreferrer", textContent: "Open site" }));
  return el("div", { className: "source-head" },
    el("h2", { className: "source-title", id: `h-${source.id}`, textContent: source.name }),
    source.description ? el("span", { className: "source-desc", textContent: source.description }) : null,
    meta);
}

// Feed data is scraped, so only allow http(s) links (never javascript: etc.).
function safeUrl(url) {
  try { const u = new URL(url); return u.protocol === "https:" || u.protocol === "http:" ? u.href : null; }
  catch { return null; }
}

function card(item, index, color) {
  const node = $("#card-tpl").content.firstElementChild.cloneNode(true);
  if (index === 0) node.classList.add("lead");
  node.querySelector(".rank").textContent = `#${index + 1}`;
  node.querySelector(".metric").textContent = item.metric ?? "";
  const link = node.querySelector(".card-link");
  const href = safeUrl(item.url);
  if (href) link.href = href;
  link.textContent = item.title;
  node.querySelector(".card-desc").textContent = item.description ?? "";
  node.querySelector(".details").replaceChildren(...item.details.filter(Boolean).map((d) => el("li", { textContent: d })));
  if (safeUrl(item.discussion_url)) {
    const d = node.querySelector(".discuss");
    d.href = safeUrl(item.discussion_url);
    d.textContent = item.discussion_label || "Discussion";
  }
  return node;
}

function renderSection(source) {
  const feed = state.feeds.get(source.id);
  const sec = document.querySelector(`.source[data-id="${source.id}"]`);
  sec.replaceChildren(sectionHead(source, feed));

  if (!feed) {  // still loading
    sec.append(el("div", { className: "grid" }, ...Array.from({ length: 4 }, () => el("div", { className: "skeleton" }))));
    return;
  }
  if (!feed.items.length) {
    const retry = el("button", { type: "button", textContent: state.mode === "static" ? "Refresh now" : "Try again" });
    retry.addEventListener("click", () => state.mode === "static" ? refreshViaActions() : loadSource(source, true));
    sec.append(el("div", { className: "notice" },
      el("span", { textContent: feed.error ? `Couldn't load ${source.name}. ${feed.error}` : "Nothing here right now." }),
      retry));
    return;
  }

  const showAll = state.expanded.has(source.id);
  const limit = initialCount();
  const items = showAll ? feed.items : feed.items.slice(0, limit);
  sec.append(el("div", { className: "grid" }, ...items.map((it, i) => card(it, i, source.color))));

  const hidden = feed.items.length - limit;
  if (hidden > 0) {
    const more = el("button", { type: "button", className: "more",
      textContent: showAll ? "Show fewer" : `Show ${hidden} more` });
    more.addEventListener("click", () => {
      showAll ? state.expanded.delete(source.id) : state.expanded.add(source.id);
      renderSection(source);
    });
    sec.append(more);
  }
}

/* ---------- Status line ---------- */
function setStatus(text, tone) {
  const s = $("#status");
  s.hidden = !text;
  s.textContent = text || "";
  if (tone) s.dataset.tone = tone; else delete s.dataset.tone;
}

function setBusy(busy, label) {
  const btn = $("#refresh-all");
  btn.disabled = busy;
  if (busy) btn.setAttribute("aria-busy", "true"); else btn.removeAttribute("aria-busy");
  $("#refresh-label").textContent = label || (state.mode === "static" ? "Refresh now" : "Refresh all");
}

/* ---------- Server mode (uvicorn) ---------- */
async function loadSource(source, refresh = false) {
  if (refresh) { state.feeds.delete(source.id); renderSection(source); renderSummary(); }
  try {
    const res = await fetch(`api/feed/${encodeURIComponent(source.id)}${refresh ? "?refresh=true" : ""}`);
    if (!res.ok) throw new Error(`Server answered ${res.status}.`);
    state.feeds.set(source.id, await res.json());
  } catch (err) {
    state.feeds.set(source.id, { source, items: [], error: err.message || "Network error." });
  }
  renderSection(source);
  renderSummary();
  renderFilters();
}

async function loadAll(refresh = false) {
  setBusy(true, "Refreshing…");
  await Promise.all(state.sources.map((s) => loadSource(s, refresh)));
  setBusy(false);
}

/* ---------- Static mode (GitHub Pages) ---------- */
async function fetchStaticFeed(bustCache = false) {
  const url = bustCache ? `data/feed.json?t=${Date.now()}` : "data/feed.json";
  const res = await fetch(url, { cache: bustCache ? "no-store" : "default" });
  if (!res.ok) throw new Error("No feed has been published yet. Run the workflow once on GitHub.");
  return res.json();
}

function applyStaticFeed(data) {
  state.site = data;
  state.sources = data.feeds.map((f) => f.source);
  state.feeds = new Map(data.feeds.map((f) => [f.source.id, f]));
}

const TOKEN_KEY = "dailystop.githubToken";
const readToken = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
const writeToken = (t) => { try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch {} };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function gh(path, token, options = {}) {
  return fetch(`https://api.github.com${path}`, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
}

function ghError(status) {
  const messages = {
    401: "GitHub rejected the saved token. It may have expired, so add a new one.",
    403: "The token can't start workflows. It needs Actions set to Read and write.",
    404: "GitHub can't find the workflow with this token. Check it has access to this repo.",
    422: "GitHub refused to start the workflow. Check it still has a workflow_dispatch trigger.",
  };
  return new Error(messages[status] || `GitHub answered with HTTP ${status}.`);
}

function workflowPage() {
  const { repo, workflow } = state.site || {};
  return repo ? `https://github.com/${repo}/actions/workflows/${workflow || "refresh.yml"}` : "https://github.com";
}

async function findRun(repo, workflow, token, runId, startedAt) {
  if (runId) {
    const res = await gh(`/repos/${repo}/actions/runs/${runId}`, token);
    if (!res.ok) throw ghError(res.status);
    return res.json();
  }
  const res = await gh(`/repos/${repo}/actions/workflows/${workflow}/runs?event=workflow_dispatch&per_page=5`, token);
  if (!res.ok) throw ghError(res.status);
  const { workflow_runs = [] } = await res.json();
  // allow a minute of clock difference between this device and GitHub
  return workflow_runs.find((r) => new Date(r.created_at) >= startedAt - 60_000) || null;
}

async function refreshViaActions() {
  const { repo, workflow = "refresh.yml", ref = "main", generated_at: previous } = state.site || {};
  if (!repo) {
    setStatus("This page doesn't know its repo yet. Run the workflow once on GitHub first.", "error");
    return;
  }
  const token = readToken();
  if (!token) { openTokenDialog(); return; }

  setBusy(true, "Starting…");
  setStatus("Asking GitHub to start the refresh workflow…");
  const startedAt = Date.now();
  try {
    const res = await gh(`/repos/${repo}/actions/workflows/${workflow}/dispatches`, token, {
      method: "POST",
      body: JSON.stringify({ ref }),
    });
    if (!res.ok) throw ghError(res.status);
    let runId = null;
    if (res.status === 200) { try { runId = (await res.json()).workflow_run_id ?? null; } catch {} }

    // 1. Wait for the workflow run (fetch sources + deploy to Pages) to finish
    let run = null;
    for (let i = 0; i < 90; i++) {           // up to ~12 minutes
      await sleep(8000);
      run = await findRun(repo, workflow, token, runId, startedAt);
      if (!run) { setStatus("Waiting for GitHub to queue the workflow…"); continue; }
      runId = run.id;
      if (run.status === "completed") break;
      setBusy(true, "Refreshing…");
      setStatus(run.status === "in_progress"
        ? "Fetching sources and publishing. This usually takes 1–2 minutes."
        : "Waiting for a GitHub runner…");
    }
    if (!run || run.status !== "completed") throw new Error("The workflow is taking longer than usual. It will finish in the background.");
    if (run.conclusion !== "success") throw new Error(`The workflow ended with "${run.conclusion}". Open it on GitHub to see why.`);

    // 2. Wait until GitHub Pages serves the new feed.json
    setStatus("Published. Loading the new picks…");
    let data = null;
    for (let i = 0; i < 20; i++) {
      data = await fetchStaticFeed(true);
      if (data.generated_at !== previous) break;
      await sleep(6000);
    }
    applyStaticFeed(data);
    state.sources.forEach(renderSection);
    renderFilters();
    renderSummary();
    setStatus(data.generated_at !== previous ? "Up to date." : "The workflow finished, but Pages is still serving the old feed. Reload in a minute.");
    setTimeout(() => { if ($("#status").textContent === "Up to date.") setStatus(null); }, 4000);
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setBusy(false);
  }
}

/* ---------- Token dialog ---------- */
function openTokenDialog() {
  const dialog = $("#token-dialog");
  const saved = !!readToken();
  $("#repo-name").textContent = state.site?.repo || "this repo";
  $("#workflow-link").href = workflowPage();
  $("#token-input").value = "";
  $("#token-forget").hidden = !saved;
  $("#token-save").textContent = saved ? "Replace and refresh" : "Save and refresh";
  dialog.returnValue = "";
  dialog.showModal();
}

function setupTokenDialog() {
  const dialog = $("#token-dialog");
  const btn = $("#token-btn");
  const syncButton = () => { btn.dataset.connected = String(!!readToken()); };
  btn.hidden = false;
  syncButton();
  btn.addEventListener("click", openTokenDialog);
  $("#token-forget").addEventListener("click", () => {
    writeToken(null); syncButton(); dialog.close("cancel");
    setStatus("Removed the saved token from this browser.");
  });
  dialog.addEventListener("close", () => {
    const token = $("#token-input").value.trim();
    $("#token-input").value = "";
    if (dialog.returnValue === "save" && token) {
      writeToken(token); syncButton(); refreshViaActions();
    }
  });
}

/* ---------- Start ---------- */
async function detectMode() {
  try {
    const res = await fetch("api/sources");
    if (res.ok && (res.headers.get("content-type") || "").includes("json")) {
      state.sources = await res.json();
      return "server";
    }
  } catch {}
  return "static";
}

function buildPage() {
  $("#feed").replaceChildren(...state.sources.map(sectionShell));
  state.sources.forEach(renderSection);
  renderFilters();
  renderSummary();
  let lastCount = initialCount(), t;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      if (initialCount() !== lastCount) { lastCount = initialCount(); state.sources.forEach(renderSection); }
    }, 150);
  });
}

async function init() {
  renderMasthead();
  state.mode = await detectMode();
  setBusy(false);

  if (state.mode === "static") {
    try {
      applyStaticFeed(await fetchStaticFeed());
    } catch (err) {
      $("#summary").textContent = err.message;
    }
    setupTokenDialog();
    $("#refresh-all").addEventListener("click", refreshViaActions);
    if (state.sources.length) buildPage();
    return;
  }

  if (!state.sources.length) {
    $("#summary").textContent = "No sources are enabled. Add one in app/sources/.";
    return;
  }
  $("#refresh-all").addEventListener("click", () => loadAll(true));
  buildPage();
  loadAll();
}

init();
