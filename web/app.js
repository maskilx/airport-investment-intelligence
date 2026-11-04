// Analyst workspace — vanilla ES module, no build step.
// Renders only structured results from the API: answers, findings, charts (Vega-Lite specs built server-side from
// findings), provenance and memory. Nothing numeric is computed or invented in the browser.

const $ = (s, el = document) => el.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) el.append(c.nodeType ? c : document.createTextNode(c));
  return el;
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// ⟦F12|20.6%⟧ markers -> clickable evidence chips; light markdown (**bold**, "- " lists, paragraphs)
function rich(text) {
  const inline = (t) => esc(t)
    .replace(/⟦(F\d+)\|([^⟧]*)⟧/g, (_, id, v) => `<button class="chip" data-fid="${id}" title="${id} — open evidence">${v}</button>`)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  const out = [];
  for (const para of String(text ?? "").split(/\n{2,}/)) {
    const lines = para.split("\n");
    if (lines.every((l) => /^\s*-\s/.test(l) || !l.trim())) {
      out.push("<ul>" + lines.filter((l) => l.trim()).map((l) => `<li>${inline(l.replace(/^\s*-\s/, ""))}</li>`).join("") + "</ul>");
    } else out.push(`<p>${lines.map(inline).join("<br>")}</p>`);
  }
  return out.join("");
}
const plainText = (t) => String(t ?? "").replace(/⟦F\d+\|([^⟧]*)⟧/g, "$1").replace(/\*\*/g, "");

const state = { conv: null, running: false, health: null, findingCache: new Map(), lastCtx: null, convFindings: new Map() };

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

// ---------------------------------------------------------------- rail
async function loadHealth() {
  try {
    const hl = (state.health = await api("/api/health"));
    const b = $("#backendBadge");
    b.className = "badge " + (hl.llm ? "llm" : "offline");
    b.lastChild.textContent = hl.llm
      ? ["LLM", hl.backend, hl.model, hl.budget ? `${hl.budget.used_today}/${hl.budget.max_per_day} req today` : null].filter(Boolean).join(" · ")
      : "OFFLINE mode · rule-based planner · no LLM calls";
    b.title = hl.llm ? "Answers are planned by the LLM; every number still comes from the engine"
      : "Rule-based demo planner — no model calls. Set AIRPORT_MODEL=gemini for open-ended questions.";
    const built = hl.build?.built_at || hl.build?.build_finished_at || "";
    $("#buildInfo").textContent = `catalog ${hl.catalog_version}${built ? " · data built " + built.slice(0, 10) : ""}`;
  } catch { $("#backendBadge").lastChild.textContent = "API unreachable"; }
}

async function loadConvs() {
  const list = await api("/api/conversations");
  const ul = $("#convs");
  ul.replaceChildren(...list.map((c) => h("li", {}, h("button", {
    "aria-current": c.id === state.conv ? "true" : "false", title: c.title || "Untitled",
    onclick: () => openConv(c.id),
  }, c.title || "Untitled analysis"))));
}

// ---------------------------------------------------------------- empty state
const SUGGESTIONS = [
  ["Ranking", "Which airports in New England are strong candidates for terminal expansion?"],
  ["Comparison", "Compare LA and Santa Ana airport congestion levels."],
  ["Definition-sensitive", "What percentage of flights out of Anchorage are long-haul?"],
  ["Inference with limits", "What is the unmet flight demand at SFO, and why?"],
];
function renderEmpty() {
  $("#turns").replaceChildren(h("div", { class: "empty" },
    h("div", { class: "eyebrow" }, "Evidence-first airport analysis"),
    h("h2", { html: "Ask a question. Get an answer you can <em>audit</em>." }),
    h("p", { class: "lede" }, "Rankings, comparisons, trends and screens computed by a deterministic engine over BTS, FAA, Census and BEA data. " +
      "Every figure is a finding you can open: definition, period, inputs, source dataset and the exact file it came from."),
    h("div", { class: "sugg" }, SUGGESTIONS.map(([k, q]) => h("button", { onclick: () => ask(q) }, h("small", {}, k), q))),
    h("div", { class: "principles" },
      h("div", {}, h("b", {}, "Numbers from findings"), "The model never writes a number; a validator rejects any that is not a cited finding."),
      h("div", {}, h("b", {}, "Facts ≠ hypotheses"), "Claims are labelled fact, inference or hypothesis; forecasts and estimates are flagged."),
      h("div", {}, h("b", {}, "Long-memory follow-ups"), "“That airport”, corrections and earlier findings carry over without resending history.")),
  ));
}

// ---------------------------------------------------------------- conversations
async function openConv(id) {
  state.conv = id;
  closeDrawers();
  const c = await api(`/api/conversations/${id}`);
  $("#convTitle").textContent = c.title || "Untitled analysis";
  const box = $("#turns");
  box.replaceChildren();
  for (const t of c.turns) {
    const el = turnShell(t.turn, t.question);
    box.append(el);
    const strips = el.querySelector(".strips");
    strips.querySelector(".status").textContent = `${t.tool_calls.length} tool calls · ${t.latency_s ?? "?"}s`;
    strips.querySelector(".pulse").classList.add("off");
    for (const tc of t.tool_calls) addStrip(strips, { name: tc.tool, input: {} }, { ok: !tc.error, elapsed_s: tc.elapsed_s, digest: tc.error ? { error: tc.error } : {} });
    renderAnswer(el, { kind: t.kind, ...(t.answer || {}), usage: t.usage, latency_s: t.latency_s });
    if (t.context) setCtx(t.context);
  }
  if (!c.turns.length) renderEmpty();
  box.scrollTop = box.scrollHeight;
  loadConvs();
}

function turnShell(n, question) {
  const el = h("article", { class: "turn" },
    h("div", { class: "q" }, h("span", { class: "n" }, `Q${String(n).padStart(2, "0")}`), h("span", { class: "text" }, question)),
    h("details", { class: "strips" },
      h("summary", {}, h("span", { class: "chev" }, "▸"), h("span", { class: "pulse" }), h("span", { class: "status" }, "Planning…"),
        h("span", { class: "count" }, ""))));
  return el;
}

const TOOL_TEXT = {
  resolve_entities: (i) => (i.terms || []).join(", ") || (i.group ? JSON.stringify(i.group) : ""),
  run_analysis: (i) => { const s = i.spec || i; return [s.op, (s.metrics || []).map((m) => (typeof m === "string" ? m : m.id)).join(", "),
    s.entities?.airports ? s.entities.airports.join(" · ") : s.entities?.group ? Object.values(s.entities.group).join(" ") : ""].filter(Boolean).join("  ▸  "); },
  derive: (i) => `${i.op}(${(i.findings || []).join(", ")})`,
  get_finding: (i) => i.id, recall: (i) => `“${i.query}”`, update_memory: (i) => `${i.action}: ${i.text || i.id || ""}`,
  query_sql: (i) => (i.sql || "").slice(0, 120), describe_catalog: (i) => i.metric || "catalog",
  compose_answer: () => "validate grounding · render answer", web_search: (i) => `“${i.query}”`, fetch_page: (i) => i.url,
};

function addStrip(strips, start, fin) {
  const cls = start.name === "compose_answer" ? "answer" : ["recall", "update_memory"].includes(start.name) ? "mem" : "";
  const meta = h("span", { class: "meta" });
  const row = h("div", { class: `strip ${cls} ${fin ? (fin.ok ? "" : "err") : "run"}` }, h("span", { class: "lane" }),
    h("span", { class: "tool" }, start.name), h("span", { class: "what", title: (TOOL_TEXT[start.name] || (() => ""))(start.input || {}) },
      (TOOL_TEXT[start.name] || (() => ""))(start.input || {})), meta);
  strips.append(row);
  if (fin) finishStrip(row, fin);
  return row;
}
function finishStrip(row, fin) {
  row.classList.remove("run");
  if (!fin.ok) row.classList.add("err");
  const meta = row.querySelector(".meta");
  const d = fin.digest || {};
  meta.replaceChildren(
    d.error ? h("span", { class: "e" }, d.error) : d.findings?.length ? `${d.findings.length} finding${d.findings.length > 1 ? "s" : ""}` : "",
    fin.elapsed_s != null ? `  ${fin.elapsed_s}s` : "");
  if (fin.result) {
    const btn = h("button", { class: "more", onclick: () => {
      const pre = row.querySelector("pre");
      if (pre) pre.remove(); else row.append(h("pre", {}, JSON.stringify(fin.result, null, 1).slice(0, 20000)));
    } }, "result");
    meta.append(btn);
  }
}

// ---------------------------------------------------------------- asking (SSE over fetch)
async function ask(text, opts = {}) {
  text = text.trim();
  if (!text || state.running) return;
  if (!state.conv) {
    state.conv = (await api("/api/conversations", { method: "POST" })).id;
    $("#convTitle").textContent = text.slice(0, 80);
    $("#turns").replaceChildren();
  }
  if ($(".empty")) $("#turns").replaceChildren();
  setRunning(true);
  const n = document.querySelectorAll(".turn").length + 1;
  const el = turnShell(n, text);
  const strips = el.querySelector(".strips");
  strips.open = true;
  $("#turns").append(el);
  el.scrollIntoView({ block: "start" });
  const rows = new Map();
  let tools = 0;
  const status = (t) => { strips.querySelector(".status").textContent = t; };
  try {
    const resp = await fetch(`/api/conversations/${state.conv}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, ...(opts.clientTurnId ? { client_turn_id: opts.clientTurnId } : {}) }) });
    if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const line = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const e = JSON.parse(line.slice(6));
        if (e.type === "context") { setCtx(e); status("Context assembled — planning"); }
        else if (e.type === "model_request") status(`Model step ${e.step}…`);
        else if (e.type === "thinking") strips.append(h("div", { class: "thought" }, e.text));
        else if (e.type === "tool_started") { tools++; rows.set(e.id, addStrip(strips, e)); status(`Running ${e.name}…`); }
        else if (e.type === "tool_finished") { const r = rows.get(e.id); if (r) finishStrip(r, e); }
        else if (e.type === "memory_compacted") strips.append(h("div", { class: "thought" }, `Memory compacted: turns ≤ ${e.upto_turn} summarised (${e.method}); findings unchanged.`));
        else if (e.type === "error") strips.append(h("div", { class: "thought" }, `Error: ${e.message}`));
        else if (e.type === "duplicate") { el.remove(); }       // a reconnect re-sent a turn the server already has
        else if (e.type === "answer") {
          status(`${tools} tool calls · ${e.latency_s}s · ${e.usage?.requests ?? 0} ${state.health && !state.health.llm ? "planner steps" : "model requests"}`);
          renderAnswer(el, e);
          strips.open = false;
          if (opts.voice || voice.on || $("#speakToggle").checked) speakAnswer(e);
        }
      }
    }
  } catch (err) {
    el.append(h("div", { class: "answer err-card plain-answer" }, /fetch|network/i.test(err.message)
      ? "Cannot reach the local server. Is it running? Start it with ./scripts/start.sh, then ask again (earlier answers are kept)."
      : `Request failed: ${err.message}`));
  } finally {
    strips.querySelector(".pulse").classList.add("off");
    setRunning(false);
    voiceTurnDone();
    loadConvs();
    if (currentTab() === "memory") showMemory();
  }
}

function setRunning(on) {
  state.running = on;
  const b = $("#sendBtn");
  b.textContent = on ? "Stop" : "Ask";
  b.classList.toggle("stop", on);
  b.type = on ? "button" : "submit";
}

// ---------------------------------------------------------------- answer rendering
const KIND_LABEL = { answer: "grounded answer", clarification: "clarification", fallback: "not established", stopped: "stopped", error: "provider error" };

function renderAnswer(turnEl, e) {
  const s = e.structured;
  if (s?.evidence_detail) for (const f of s.evidence_detail) state.convFindings.set(f.id, f);
  let card;
  if (!s) {
    card = h("div", { class: `answer ${e.kind === "error" ? "err-card" : ""}` },
      h("div", { class: "a-head" }, h("h3", {}, e.kind === "clarification" ? "Before going further" : KIND_LABEL[e.kind] || e.kind),
        h("span", { class: "kind" }, KIND_LABEL[e.kind] || e.kind)),
      h("div", { class: "body", html: rich(e.markdown) }));
  } else {
    card = h("div", { class: "answer" },
      h("div", { class: "a-head" }, h("h3", {}, s.headline), h("span", { class: "kind" }, KIND_LABEL[e.kind] || e.kind)),
      h("div", { class: "body", html: rich(s.body) }));
    if (s.investigation) {                 // objective -> investigated -> established -> unknown -> next step
      const iv = s.investigation, li = (k, t) => iv[k]?.length ? h("li", {}, h("strong", {}, `${t}: `),
        h("span", { html: iv[k].map((x) => rich(x).replace(/^<p>|<\/p>$/g, "")).join("; ") })) : null;
      card.append(h("div", { class: "section inv" }, h("h4", {}, "Investigation summary"), h("ul", { class: "plain" },
        h("li", {}, h("strong", {}, `Objective (${iv.question_type}): `), h("span", { html: rich(iv.objective).replace(/^<p>|<\/p>$/g, "") })),
        li("investigated", "Investigated"), li("established", "Established"), li("unknown", "Unknown"),
        iv.next_step ? h("li", {}, h("strong", {}, "Most useful next step: "), iv.next_step) : null)));
    }
    if (e.charts?.length) {
      const sec = h("div", { class: "section" }, h("h4", {}, "Charts — values are findings; click a mark to inspect"), h("div", { class: "charts" }));
      card.append(sec);
      for (const c of e.charts) sec.lastChild.append(chartEl(c));
    }
    if (s.claims?.length) {
      // separate what the data shows from what is interpreted from it (and from outside sources)
      const groups = [
        ["Evidence: measured and calculated", ["fact", "comparison", "ranking"]],
        ["Interpretation and judgment", ["assessment", "inference", "hypothesis"]],
        ["External sources (web)", ["external"]],
      ];
      for (const [title, kinds] of groups) {
        const cs = s.claims.filter((c) => kinds.includes(c.kind));
        if (!cs.length) continue;
        card.append(h("div", { class: "section" }, h("h4", {}, title), h("ul", { class: "claims" }, cs.map(claimEl))));
      }
    }
    if (s.external?.length) {
      card.append(h("div", { class: "section" }, h("h4", {}, "External sources — web, not part of the internal datasets"),
        h("ul", { class: "plain" }, s.external.map((w) => h("li", {}, h("button", { class: "chip ext", "data-fid": w.id }, w.id), " ",
          h("a", { href: w.url, target: "_blank", rel: "noopener noreferrer" }, w.title), ` — ${w.domain}, retrieved ${w.retrieved_at.slice(0, 10)}`)))));
    }
    if (s.scoring_method?.length) {
      card.append(h("div", { class: "section" }, h("details", { class: "fold", open: true },
        h("summary", {}, "How the score is calculated (deterministic, config/screening.toml)"),
        h("ul", { class: "plain" }, s.scoring_method.map((m) => h("li", {}, m))))));
    }
    const lists = [["Assumptions", s.assumptions], ["Limitations (what the data cannot establish)", s.limitations]].filter(([, v]) => v?.length);
    for (const [k, v] of lists) card.append(h("div", { class: "section" }, h("h4", {}, k), h("ul", { class: "plain" }, v.map((x) => h("li", { html: rich(x).replace(/^<p>|<\/p>$/g, "") })))));
    if (s.evidence_detail?.length) {
      const tbl = h("table", { class: "ev" }, h("thead", {}, h("tr", {}, ["Id", "Finding", "Value", "Class", "Source", "Coverage"].map((x) => h("th", {}, x)))),
        h("tbody", {}, s.evidence_detail.map((f) => h("tr", { "data-fid": f.id },
          h("td", { class: "id" }, f.id), h("td", {}, f.label), h("td", { class: "v" }, f.formatted),
          h("td", {}, h("span", { class: `cls ${f.class}` }, f.class)), h("td", { class: "mono", style: "font-size:11px" }, (f.sources || []).join("; ")),
          h("td", { class: "mono", style: "font-size:11px" }, f.coverage?.ratio != null ? `${Math.round(f.coverage.ratio * 100)}% (${f.coverage.window ?? ""})` : "")))));
      const fold = h("details", { class: "fold" }, h("summary", {}, `Evidence (${s.evidence_detail.length})`), h("div", { class: "tscroll" }, tbl));
      if (s.evidence_detail.length <= 8) fold.open = true;
      card.append(h("div", { class: "section" }, fold));
    }
    if (s.caveats?.length || Object.keys(s.methodology || {}).length) {
      card.append(h("div", { class: "section" }, h("details", { class: "fold" }, h("summary", {}, "Methodology & caveats"),
        h("ul", { class: "plain" }, Object.entries(s.methodology || {}).map(([k, v]) => h("li", {}, h("span", { class: "mono" }, k), ": ", v))),
        ...(s.caveats || []).map((c) => h("p", { class: "caveat" }, c)))));
    }
  }
  const foot = h("div", { class: "a-foot" },
    e.usage ? h("span", {}, state.health && !state.health.llm
      ? `${e.usage.requests ?? 0} offline planner steps · no model API calls`
      : `${e.usage.requests ?? 0} model requests · ${(e.usage.input_tokens ?? 0).toLocaleString()} in / ${(e.usage.output_tokens ?? 0).toLocaleString()} out tokens`) : "",
    e.latency_s != null ? h("span", {}, `${e.latency_s}s`) : "",
    state.health ? h("span", {}, state.health.llm ? `planner: ${state.health.backend}` : "planner: offline rules (no LLM)") : "",
    h("button", { onclick: () => navigator.clipboard?.writeText(e.markdown || "") }, "copy markdown"));
  card.append(foot);
  turnEl.append(card);
}

const TAG_HELP = {
  Measured: "Read directly from a published dataset (e.g. BTS, FAA), summed over the stated period.",
  Calculated: "Computed by the analytics engine from measured data (a ratio, change or score); the formula is in Methodology.",
  "Forecast (FAA)": "An official FAA Terminal Area Forecast value: a projection, not an observation.",
  "Comparison (computed)": "The direction (higher / lower / similar) is checked by code against the cited values.",
  "Ranking (computed)": "Rank, set size and robustness are written by code from the rank/screen result.",
  Interpretation: "A reading of the cited findings; it adds no new numbers.",
  "Hypothesis (not established by the data)": "A possible explanation with competing alternatives; the data cannot confirm it.",
  "Assessment (judgment on cited evidence)": "A judgment for a stated objective. Each criterion cites findings, and which option it favours is checked by code.",
  "External source": "From a fetched web page, quoted verbatim; not part of the internal datasets.",
};
const fidChips = (ids) => h("span", { class: "support" }, "[", ids.map((id) => h("button", { "data-fid": id }, id)), "]");

function claimEl(c) {
  const label = c.label || c.kind;
  const tag = h("span", { class: `tag ${c.kind}`, title: TAG_HELP[label] || "how this statement is established" }, label);
  if (c.kind === "assessment" && c.assessment) {
    const a = c.assessment;
    const fav = (x) => (!x || /^(none|neither|unclear|mixed)$/i.test(x) ? "no clear advantage" : x);
    return h("li", { class: "assess" }, tag, h("div", {},
      h("p", {}, h("strong", {}, "Objective: "), a.objective),
      h("table", { class: "ev crit" }, h("thead", {}, h("tr", {}, ["Criterion", "Favours", "Evidence", "Why it matters"].map((x) => h("th", {}, x)))),
        h("tbody", {}, a.criteria.map((k) => h("tr", {}, h("td", {}, k.name), h("td", { class: "v" }, fav(k.favors)),
          h("td", {}, fidChips(k.findings)), h("td", {}, k.why || ""))))),
      h("p", {}, h("strong", {}, "Judgment: "), a.abstain ? `No definitive recommendation: ${a.abstain_reason || "the evidence is insufficient"}.` : a.judgment),
      a.tradeoffs?.length ? h("p", {}, h("strong", {}, "Trade-offs: "), a.tradeoffs.join("; ")) : null,
      a.robustness ? h("p", {}, h("strong", { title: "Recomputed by the scoring engine under each documented weighting scenario. This is not a statistical confidence." }, "Sensitivity (computed): "),
        a.robustness.replace(/\.?$/, "."), a.robust === false ? " The preference depends on the weighting assumption." : "") : null,
      a.conditional_on?.length ? h("p", {}, h("strong", {}, "Holds only if: "), a.conditional_on.join("; ")) : null,
      a.would_change?.length ? h("p", {}, h("strong", {}, "Would change with: "), a.would_change.join("; ")) : null));
  }
  return h("li", {}, tag, h("span", {}, h("span", { html: rich(c.text).replace(/^<p>|<\/p>$/g, "") }),
    c.kind === "external" ? h("span", {}, " — ", h("q", { class: "quote" }, c.quote), " ", h("button", { class: "chip ext", "data-fid": c.source }, c.source)) : null,
    c.support?.length ? fidChips(c.support) : null));
}

function chartTheme() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n) => cs.getPropertyValue(n).trim();
  return {
    background: null, font: "Public Sans, Helvetica Neue, sans-serif",
    range: { category: [v("--blue"), v("--magenta"), v("--green"), v("--amber"), v("--ink-2")] },
    mark: { color: v("--blue") }, bar: { color: v("--blue") }, line: { color: v("--magenta"), strokeWidth: 2 },
    point: { color: v("--magenta") },
    axis: { labelColor: v("--ink-2"), titleColor: v("--ink-3"), domainColor: v("--rule-2"), tickColor: v("--rule-2"),
      gridColor: v("--rule"), gridOpacity: 0.7, labelFont: "IBM Plex Mono, monospace", labelFontSize: 10.5, titleFontSize: 10.5, titleFontWeight: 600 },
    legend: { labelColor: v("--ink-2"), titleColor: v("--ink-3"), labelFontSize: 11, orient: "bottom" },
    view: { stroke: null },
  };
}

function chartEl(c) {
  const box = h("div", { class: "chart" }, h("p", { class: "ct" }, c.title),
    h("p", { class: "cs" }, `${c.type} · ${c.findings.length} findings · ${c.findings.slice(0, 6).join(", ")}${c.findings.length > 6 ? "…" : ""}`));
  if (c.vega_lite && window.vegaEmbed) {
    const vis = h("div", { class: "vis" });
    box.append(vis);
    setTimeout(() => {          // not rAF: it never fires in a background tab, leaving charts blank
      vegaEmbed(vis, { ...c.vega_lite, config: chartTheme() }, { actions: { export: true, source: false, compiled: false, editor: false }, renderer: "svg" })
        .then(({ view }) => view.addEventListener("click", (_, item) => {
          const fid = item?.datum?.fid;
          if (fid) showFinding(String(fid).split(",")[0]);
        })).catch((err) => vis.replaceWith(h("p", { class: "note" }, `Chart could not render: ${err.message}`)));
    }, 0);
  } else {
    box.append(h("table", { class: "ev" }, h("tbody", {}, c.rows.map((r) => h("tr", { "data-fid": r.fid },
      h("td", { class: "id" }, r.fid), h("td", {}, r.label), h("td", { class: "v" }, r.formatted))))));
  }
  for (const n of c.notes || []) box.append(h("p", { class: "note" }, n));
  return box;
}

// ---------------------------------------------------------------- inspector
const currentTab = () => $(".tabs [aria-selected=true]")?.dataset.tab;
function selectTab(tab) {
  document.querySelectorAll(".tabs [role=tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
  $("#inspector").classList.add("open");
}
function emptyPane(msg) { $("#pane").replaceChildren(h("p", { class: "muted" }, msg)); }

async function showExternal(wid) {
  selectTab("evidence");
  let w;
  try { w = await api(`/api/conversations/${state.conv}/external/${wid}`); } catch (err) { return emptyPane(`${wid}: ${err.message}`); }
  $("#pane").replaceChildren(
    h("div", { class: "f-id" }, `${w.id} · external web source`),
    h("p", { class: "f-label", style: "font:600 18px/1.3 var(--f-display);margin-top:6px" }, w.title),
    h("div", { class: "src web" }, h("a", { href: w.url, target: "_blank", rel: "noopener noreferrer" }, `${w.domain} ↗`),
      h("div", { class: "p", style: "margin-top:6px" }, `Retrieved ${w.retrieved_at} · ${w.chars.toLocaleString()} characters of text · sha256 ${w.sha256.slice(0, 12)}…`),
      w.requested_url !== w.url ? h("div", { class: "p" }, `Requested ${w.requested_url} (redirected)`) : null),
    h("p", { class: "caveat" }, "External content is not validated like internal datasets. Quotes cited in answers are verified to appear verbatim in this text."),
    h("div", { class: "kicker" }, "Beginning of the fetched text"), h("pre", { class: "spec" }, w.excerpt));
}

async function showFinding(fid) {
  if (fid.startsWith("W")) return showExternal(fid);
  selectTab("evidence");
  document.querySelectorAll(".chip.on").forEach((c) => c.classList.remove("on"));
  document.querySelectorAll(`.chip[data-fid="${fid}"]`).forEach((c) => c.classList.add("on"));
  if (!state.conv) return;
  emptyPane(`Loading ${fid}…`);
  let f;
  try { f = await api(`/api/conversations/${state.conv}/findings/${fid}`); } catch (err) { return emptyPane(`${fid}: ${err.message}`); }
  const pane = $("#pane");
  pane.replaceChildren(
    h("div", { class: "f-id" }, `${f.id} · internal dataset finding`),
    h("div", { class: "f-value" }, f.formatted),
    h("p", { class: "f-label" }, f.label),
    h("dl", { class: "kv" },
      h("dt", {}, "Class"), h("dd", {}, h("span", { class: `cls ${f.epistemic_class}` }, f.epistemic_class)),
      h("dt", {}, "Metric"), h("dd", { class: "mono" }, `${f.metric_id} · v${f.formula_version}`),
      h("dt", {}, "Definition"), h("dd", {}, f.definition),
      h("dt", {}, "Period"), h("dd", {}, f.window?.label || "—"),
      h("dt", {}, "Subject"), h("dd", { class: "mono" }, Object.entries(f.subject || {}).map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("+") : v}`).join("  ")),
      f.coverage ? [h("dt", {}, "Coverage"), h("dd", {}, `${Math.round((f.coverage.ratio ?? 0) * 100)}% of departures in ${f.coverage.window ?? "window"}`)] : null,
      h("dt", {}, "Catalog"), h("dd", { class: "mono" }, f.catalog_version || "—"),
      h("dt", {}, "Status"), h("dd", {}, f.status === "stale"
        ? h("span", { class: "cls hypothesis", title: f.status_reason }, `stale: ${f.status_reason}`)
        : h("span", { class: "cls observed" }, "current")),
      f.assumptions?.length ? [h("dt", {}, "Assumptions"), h("dd", { class: "mono" }, f.assumptions.join(", "))] : null,
      f.execution ? [h("dt", {}, "Produced by"), h("dd", { class: "mono" },
        `${f.execution.tool} · ${f.execution.op}` + (f.execution.screening ? ` · ${f.execution.screening.scenario} · cfg ${f.execution.screening.config_hash}` : "")
        + ` · build ${f.execution.build?.git_rev || "?"}/${(f.execution.build?.raw_fingerprint || "").slice(0, 8)}`)] : null,
      f.cited_in_turns?.length ? [h("dt", {}, "Cited in"), h("dd", {}, f.cited_in_turns.map((t) => `Q${String(t).padStart(2, "0")}`).join(", "))] : null),
  );
  if (f.input_findings?.length) {
    pane.append(h("div", { class: "kicker" }, "Derived from"), h("ul", { class: "plain" },
      f.input_findings.map((i) => h("li", {}, h("button", { class: "chip", "data-fid": i.id }, i.id), " ", i.label, " = ", i.formatted))));
  }
  if (f.caveats?.length) pane.append(h("div", { class: "kicker" }, "Caveats"), ...f.caveats.map((c) => h("p", { class: "caveat" }, c)));
  pane.append(h("div", { class: "kicker" }, "Sources (from the build manifest)"));
  for (const s of f.sources_detail || []) {
    const vs = s.vintages || [];
    pane.append(h("div", { class: "src" },
      h("div", { class: "t" }, s.title || s.id),
      h("div", { class: "p" }, [s.publisher, s.license, s.cadence].filter(Boolean).join(" · ")),
      s.homepage ? h("a", { href: s.homepage, target: "_blank", rel: "noopener noreferrer" }, "Dataset page ↗") : null,
      h("div", { class: "p", style: "margin-top:6px" }, `Periods used: ${(s.periods || []).length ? `${s.periods[0]} … ${s.periods[s.periods.length - 1]} (${s.periods.length})` : "n/a"}`),
      vs.length ? h("table", {}, h("tbody", {}, vs.slice(0, 14).map((v) => h("tr", {},
        h("td", {}, v.period), h("td", { title: v.sha256 }, (v.sha256 || "").slice(0, 10)), h("td", {}, (v.stored_at || "").slice(0, 10)),
        h("td", {}, (v.links || []).length ? v.links.map((l) => h("a", { href: l.url, target: "_blank", rel: "noopener noreferrer",
          title: l.note || l.url, style: "margin-right:6px" }, `${l.label} ↗`)) : "local file"))))) : null,
      s.access === "form" ? h("p", { class: "note" }, `Access: ${s.access_note}.`) : null,
      vs.length > 14 ? h("div", { class: "p" }, `+ ${vs.length - 14} more vintages`) : null));
  }
  if (f.spec) pane.append(h("div", { class: "kicker" }, "Reproducing analysis spec"), h("pre", { class: "spec" }, JSON.stringify(f.spec, null, 2)));
}

async function showMemory() {
  selectTab("memory");
  if (!state.conv) return emptyPane("Memory appears once an analysis starts.");
  const m = await api(`/api/conversations/${state.conv}/memory`);
  const b = m.budget, st = m.context_stats;
  const tot = b.total, pr = (x) => `${Math.min(100, (100 * x) / tot).toFixed(1)}%`;
  const last = state.lastCtx || st;
  $("#pane").replaceChildren(...[
    h("div", { class: "kicker", style: "margin-top:0" }, "Context budget (last request)"),
    h("div", { class: "gauge" }, h("i", { style: `width:${pr(last.recent_tokens)};background:var(--blue)` }), h("i", { style: `width:${pr(last.memory_tokens)};background:var(--magenta)` })),
    h("div", { class: "legend" }, h("span", { style: "--c:var(--blue)" }, `recent turns verbatim ${last.recent_tokens}`), h("span", { style: "--c:var(--magenta)" }, `memory block ${last.memory_tokens}`),
      h("span", {}, `budget ${tot} tokens`)),
    h("p", { class: "muted" }, `${last.turns_verbatim} of ${last.turns_total} earlier turns sent verbatim, ${last.turns_summarised} summarised; ${last.findings_listed} of ${last.findings_total} findings indexed. Older tool payloads are replaced by pointers to stored findings — the full transcript stays on disk.`),
    h("div", { class: "kicker" }, "Entities in focus"),
    h("div", { class: "ents" }, m.state.entities.length ? m.state.entities.map((e) => h("span", { class: "ent", title: e.label }, e.kind === "group" ? e.label : e.key, " ", h("small", {}, `Q${e.first}–Q${e.last}`))) : h("span", { class: "muted" }, "none yet")),
    h("div", { class: "kicker" }, "Assumptions"),
    ...(m.state.assumptions.length ? m.state.assumptions.map((a) => h("div", { class: `asm ${a.status}` }, h("span", { class: "mono" }, `${a.id} · ${a.status}${a.superseded_by ? " → " + a.superseded_by : ""} · Q${a.turn}`), h("br"), a.text)) : [h("p", { class: "muted" }, "none recorded")]),
    (m.state.lists || []).length ? h("div", { class: "kicker" }, "Ordered results (for “the top two”, “the second one”)") : null,
    ...(m.state.lists || []).slice(-3).map((L) => h("div", { class: "asm" }, h("span", { class: "mono" }, `Q${L.turn} · ${L.label}`), h("br"),
      L.items.slice(0, 12).map((c, i) => h("span", {}, i ? " › " : "", L.scores[i] ? h("button", { class: "chip", "data-fid": L.scores[i] }, c) : c)))),
    m.state.decisions.length ? h("div", { class: "kicker" }, "Decisions") : null,
    ...m.state.decisions.map((d) => h("div", { class: "asm" }, d.text, " ", h("span", { class: "support" }, d.support.join(", ")))),
    h("div", { class: "kicker" }, "Rolling summary"),
    m.summary ? h("div", {}, h("p", { class: "muted" }, `turns ≤ ${m.summary.upto_turn} · ${m.summary.method} · validated to contain no numbers`), h("pre", { class: "spec" }, m.summary.text))
      : h("p", { class: "muted" }, "Not needed yet — all turns fit in the verbatim window."),
    h("details", { class: "fold" }, h("summary", {}, "Memory block sent with the next question"), h("pre", { class: "spec" }, m.memory_block || "(empty)")),
    h("p", { class: "muted", style: "margin-top:14px" }, `Session usage: ${m.usage.requests} model requests, ${m.usage.input_tokens} input / ${m.usage.output_tokens} output tokens.`),
  ].filter(Boolean));
}

async function showSources() {
  selectTab("sources");
  const list = await api("/api/sources");
  $("#pane").replaceChildren(h("p", { class: "muted", style: "margin-top:0" }, "Internal datasets used by the engine. Links are the publishers' dataset pages recorded at ingestion; each finding also lists the exact files fetched."),
    ...list.map((s) => h("div", { class: "src" }, h("div", { class: "t" }, s.title), h("div", { class: "p" }, [s.publisher, s.license, s.cadence].filter(Boolean).join(" · ")),
      h("div", { class: "p mono" }, s.id), s.homepage ? h("a", { href: s.homepage, target: "_blank", rel: "noopener noreferrer" }, "Dataset page ↗") : null)));
}

function setCtx(c) {
  state.lastCtx = c;
  const tot = 24000;
  $("#ctxMeter .bar i").style.width = `${Math.min(100, (100 * c.recent_tokens) / tot)}%`;
  $("#ctxMeter .bar b").style.left = `${Math.min(100, (100 * c.recent_tokens) / tot)}%`;
  $("#ctxMeter .bar b").style.width = `${Math.min(100, (100 * c.memory_tokens) / tot)}%`;
  $("#ctxText").textContent = `ctx ${(c.recent_tokens + c.memory_tokens).toLocaleString()} tok · ${c.turns_verbatim}/${c.turns_total} turns`;
}

// ---------------------------------------------------------------- live voice: another interface to the SAME agent
// Chained pipeline (docs/voice-architecture-review.md): speech -> transcript -> the existing /messages endpoint (same
// conversation, tools, validation) -> the server's spoken rendering of the VALIDATED answer -> browser speech synthesis.
// Server speech-to-text (Groq Whisper) when configured, with Silero VAD in the browser; otherwise Web Speech recognition.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const voice = { on: false, state: "off", cfg: null, rec: null, vad: null, queue: null, lastFinal: "", lastFinalAt: 0,
  speaking: "", pending: 0, retry: 0, sentIds: new Set(), mode: "" };
const VSTATE = { off: "Voice off", connecting: "Connecting microphone…", listening: "Listening: speak naturally",
  processing: "Working on it…", speaking: "Speaking: talk or press Esc to interrupt",
  disconnected: "Microphone connection lost: reconnecting", error: "Voice unavailable" };
function vstate(s, detail) {
  voice.state = s;
  const bar = $("#voiceBar");
  bar.dataset.state = s;
  $("#voiceState").textContent = VSTATE[s] + (detail ? ` · ${detail}` : "");
  $("#micBtn").classList.toggle("on", voice.on);
}
function vtranscript(t, final) { const el = $("#voiceText"); el.textContent = t ? `“${t}”` : ""; el.classList.toggle("final", !!final); }
const words = (t) => (t || "").toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter(Boolean);
function isEcho(t) {            // the microphone hearing our own speech output is not a user turn
  if (!voice.speaking) return false;
  const w = words(t), said = new Set(words(voice.speaking));
  return w.length > 0 && w.filter((x) => said.has(x)).length / w.length >= 0.6;
}
async function voiceStart() {
  voice.on = true; $("#voiceBar").hidden = false; vstate("connecting");
  try { voice.cfg = voice.cfg || await api("/api/voice/config"); } catch { voice.cfg = { stt: "browser" }; }
  if (voice.cfg.stt === "groq" && await startVAD()) return;
  startBrowserSR();
}
function voiceStop() {
  voice.on = false; stopSpeaking();
  try { voice.rec?.abort(); } catch {}
  voice.rec = null; voice.vad?.pause();
  vstate("off"); $("#voiceBar").hidden = true; vtranscript("");
}
function startBrowserSR() {
  if (!SR) { vstate("error", "this browser has no speech recognition: use Chrome or Safari, or type your question"); return; }
  voice.mode = "browser";
  const r = new SR(); voice.rec = r;
  r.lang = "en-US"; r.continuous = true; r.interimResults = true;
  r.onstart = () => { voice.retry = 0; if (voice.state === "connecting" || voice.state === "disconnected") vstate(state.running ? "processing" : (voice.speaking ? "speaking" : "listening")); };
  r.onresult = (ev) => {
    let interim = "";
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const res = ev.results[i], t = res[0].transcript.trim();
      if (res.isFinal) { if (t) onUtterance(t, `sr-${voice.sessionId}-${i}-${t.length}`); }
      else interim += t + " ";
    }
    if (interim.trim() && !isEcho(interim)) { if (voice.state === "speaking" && words(interim).length >= 2) bargeIn(); vtranscript(interim.trim(), false); }
  };
  r.onerror = (e) => {
    if (e.error === "not-allowed" || e.error === "service-not-allowed") { voice.on = false; vstate("error", "microphone permission denied"); }
    else if (e.error !== "no-speech" && e.error !== "aborted") vstate("disconnected", e.error);
  };
  r.onend = () => {                                           // recognition stops on silence/network: keep the session alive
    if (!voice.on || voice.rec !== r) return;
    const delay = voice.state === "disconnected" ? Math.min(8000, 500 * 2 ** voice.retry++) : 150;
    setTimeout(() => { if (voice.on && voice.rec === r) { try { r.start(); } catch { startBrowserSR(); } } }, delay);
  };
  voice.sessionId = Date.now().toString(36);
  try { r.start(); } catch (e) { vstate("error", e.message); }
}
function onUtterance(text, id) {
  if (!voice.on || voice.sentIds.has(id)) return;
  voice.sentIds.add(id);
  if (isEcho(text)) return;
  const norm = words(text).join(" ");
  if (!norm || (norm === voice.lastFinal && Date.now() - voice.lastFinalAt < 5000)) return;   // double-fired final
  voice.lastFinal = norm; voice.lastFinalAt = Date.now();
  vtranscript(text, true);
  stopSpeaking();
  if (state.running) { voice.queue = { text, id }; vstate("processing", "next question queued"); return; }
  vstate("processing");
  ask(text, { clientTurnId: id, voice: true });
}
function speakAnswer(e) {
  if (!window.speechSynthesis) { if (voice.on) vstate("listening", "no speech output in this browser"); return; }
  const text = e.structured?.spoken || plainText(e.markdown || "").slice(0, 700);
  const sentences = (text.match(/[^.!?]+[.!?]*/g) || [text]).map((x) => x.trim()).filter(Boolean);
  speechSynthesis.cancel();
  voice.speaking = text; voice.pending = sentences.length;
  if (voice.on) vstate("speaking");
  const v = pickVoice();
  for (const sen of sentences) {                     // sentence by sentence: starts at once, stops mid-answer cleanly
    const u = new SpeechSynthesisUtterance(sen);
    u.lang = "en-US"; u.rate = 1.04; if (v) u.voice = v;
    u.onend = u.onerror = () => { if (--voice.pending <= 0) { voice.speaking = ""; if (voice.on && voice.state === "speaking") vstate("listening"); } };
    speechSynthesis.speak(u);
  }
}
function stopSpeaking() { if (window.speechSynthesis) speechSynthesis.cancel(); voice.speaking = ""; voice.pending = 0; }
function bargeIn() { stopSpeaking(); if (voice.on) vstate("listening", "interrupted"); }
function pickVoice() {
  const vs = (window.speechSynthesis?.getVoices() || []).filter((x) => /^en[-_]US/i.test(x.lang));
  return vs.find((x) => /Samantha|Ava|Allison|Zoe|Google US English/i.test(x.name)) || vs[0] || null;
}
function voiceTurnDone() {
  if (!voice.on) return;
  if (voice.queue) { const q = voice.queue; voice.queue = null; vstate("processing"); ask(q.text, { clientTurnId: q.id, voice: true }); return; }
  if (voice.state === "processing") vstate("listening");
}
// --- server speech-to-text path: Silero VAD in the browser decides when the user has finished speaking
const loadScript = (src) => new Promise((res, rej) => { const s = document.createElement("script"); s.src = src; s.onload = res; s.onerror = () => rej(new Error(`load ${src}`)); document.head.append(s); });
const ORT = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.22.0/dist/";
const VADJS = "https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.31/dist/";
async function startVAD() {
  try {
    if (!window.vad) { await loadScript(ORT + "ort.wasm.min.js"); await loadScript(VADJS + "bundle.min.js"); }
    voice.vad = await window.vad.MicVAD.new({
      model: "v5", baseAssetPath: VADJS, onnxWASMBasePath: ORT, redemptionMs: 600, minSpeechMs: 300,
      onSpeechRealStart: () => { if (voice.state === "speaking") bargeIn(); vtranscript("…", false); },
      onSpeechEnd: (audio) => transcribeUtterance(audio),
    });
    voice.vad.start(); voice.mode = "server";
    vstate("listening", `speech-to-text: ${voice.cfg.stt_model}`);
    return true;
  } catch (err) { console.warn("VAD unavailable; using browser recognition", err); return false; }
}
async function transcribeUtterance(audio) {
  if (audio.length < 16000 * 0.4) return;                      // < 0.4 s: a click or cough, not a question
  const id = `vad-${Date.now().toString(36)}`;
  const body = encodeWAV(audio, 16000);
  vstate(state.running ? "processing" : "processing", "transcribing");
  for (let attempt = 0; attempt < 2; attempt++) {             // same utterance id: the server never transcribes twice
    try {
      const r = await fetch("/api/voice/transcribe", { method: "POST", headers: { "Content-Type": "audio/wav", "X-Utterance-Id": id }, body });
      if (!r.ok) throw new Error(`${r.status}`);
      const j = await r.json();
      if (j.text) onUtterance(j.text, id); else vstate("listening");
      return;
    } catch (e) { vstate("disconnected", "speech-to-text failed"); await new Promise((res) => setTimeout(res, 800)); }
  }
  vstate("listening", "please repeat, or type");
}
function encodeWAV(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2), v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) { const x = Math.max(-1, Math.min(1, samples[i])); v.setInt16(44 + i * 2, x < 0 ? x * 0x8000 : x * 0x7fff, true); }
  return new Blob([buf], { type: "audio/wav" });
}
function toggleMic() { voice.on ? voiceStop() : voiceStart(); }
window.__voice = { onUtterance, bargeIn, speakAnswer, stopSpeaking, isEcho, state: () => voice.state, get: () => voice,   // test hooks
  start: () => { voice.on = true; $("#voiceBar").hidden = false; vstate("listening"); },
  disconnect: () => { vstate("disconnected", "simulated"); setTimeout(() => voice.on && vstate("listening"), 300); } };

// ---------------------------------------------------------------- wiring
function closeDrawers() { $("#rail").classList.remove("open"); }
$("#form").addEventListener("submit", (ev) => { ev.preventDefault(); const t = $("#input").value; $("#input").value = ""; autosize(); ask(t); });
$("#sendBtn").addEventListener("click", (ev) => {
  if (state.running) { ev.preventDefault(); fetch(`/api/conversations/${state.conv}/cancel`, { method: "POST" }); }
});
const autosize = () => { const t = $("#input"); t.style.height = "auto"; t.style.height = Math.min(180, t.scrollHeight) + "px"; };
$("#input").addEventListener("input", autosize);
$("#input").addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); $("#form").requestSubmit(); } });
$("#newBtn").addEventListener("click", () => { state.conv = null; $("#convTitle").textContent = "New analysis"; renderEmpty(); loadConvs(); closeDrawers(); emptyPane("Click any value, chart mark or evidence row to inspect its provenance."); });
$("#micBtn").addEventListener("click", toggleMic);
$("#voiceStopAudio").addEventListener("click", bargeIn);
$("#voiceEnd").addEventListener("click", voiceStop);
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && voice.speaking) bargeIn(); });
$("#menuBtn").addEventListener("click", () => $("#rail").classList.toggle("open"));
$("#inspBtn").addEventListener("click", () => $("#inspector").classList.toggle("open"));
$("#inspClose").addEventListener("click", () => $("#inspector").classList.remove("open"));
$("#ctxMeter").addEventListener("click", showMemory);
$("#sourcesLink").addEventListener("click", showSources);
$("#themeBtn").addEventListener("click", () => {
  const r = document.documentElement;
  const dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = dark ? "light" : "dark";
});
document.querySelectorAll(".tabs [role=tab]").forEach((b) => b.addEventListener("click", () =>
  ({ evidence: () => (state.lastFid ? showFinding(state.lastFid) : emptyPane("Click any value, chart mark or evidence row to inspect its provenance.")), memory: showMemory, sources: showSources })[b.dataset.tab]()));
document.addEventListener("click", (ev) => {
  const t = ev.target.closest("[data-fid]");
  if (t) { state.lastFid = t.dataset.fid; showFinding(t.dataset.fid); }
});

loadHealth();
loadConvs();
renderEmpty();
emptyPane("Click any value, chart mark or evidence row to inspect its provenance.");
