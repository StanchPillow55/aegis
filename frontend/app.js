const form = document.getElementById("compose-form");
const textarea = document.getElementById("compose-text");
const directiveBtn = document.getElementById("directive-btn");
const askBtn = document.getElementById("ask-btn");
const dictateBtn = document.getElementById("dictate-btn");
const dictateStatus = document.getElementById("dictate-status");
const composeHint = document.getElementById("compose-hint");
const speakToggle = document.getElementById("speak-toggle");
const result = document.getElementById("result");
const directiveText = document.getElementById("directive-text");
const disclaimerText = document.getElementById("disclaimer-text");
const directiveMode = document.getElementById("directive-mode");
const scoreRow = document.getElementById("score-row");
const todayPre = document.getElementById("today-pre");
const historyPre = document.getElementById("history-pre");
const conflictsPre = document.getElementById("conflicts-pre");
const evidencePre = document.getElementById("evidence-pre");
const thread = document.getElementById("thread");
const threadLog = document.getElementById("thread-log");
const contextPinsEl = document.getElementById("context-pins");
const imagePreview = document.getElementById("image-preview");
const composeImage = document.getElementById("compose-image");
const attachImgBtn = document.getElementById("attach-img-btn");
const pinModeBtn = document.getElementById("pin-mode-btn");
const pinBanner = document.getElementById("pin-banner");

let recognizing = false;
let recognition = null;
let imageAttachment = null;
let pinnedContexts = [];
let pinPicking = false;
let chatSessionId = localStorage.getItem("aegis_chat_session_id") || null;

function SpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function autosizeComposer() {
  textarea.style.height = "auto";
  const next = Math.min(textarea.scrollHeight, Math.min(window.innerHeight * 0.55, 28 * 16));
  textarea.style.height = `${Math.max(next, 8 * 16)}px`;
  textarea.style.overflowY = textarea.scrollHeight > next ? "auto" : "hidden";
}

textarea.addEventListener("input", autosizeComposer);
window.addEventListener("resize", autosizeComposer);
autosizeComposer();

function isSyncCommand(text) {
  const t = (text || "").trim().toLowerCase();
  if (!t) return false;
  if (["sync", "sync now", "resync", "refresh sources"].includes(t)) return true;
  return /\b(sync\s+(now|everything|all|sources?|data)|(please\s+)?(run|start|trigger|do)\s+(a\s+)?sync|refresh\s+(sources?|data|sync)|pull\s+(my\s+)?(data|fitbit|sources?))\b/.test(
    t
  );
}

async function runOnDemandSync(channel) {
  const res = await fetch("/api/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force: false }),
  });
  const data = await res.json();
  const n = (data.results || []).length;
  const ok = (data.results || []).filter((r) => r.success).length;
  return { ok, n, data, channel };
}

function renderPins() {
  contextPinsEl.innerHTML = pinnedContexts
    .map(
      (p) =>
        `<span class="pin-chip" data-id="${p.id}">${escapeHtml(p.label)}` +
        `<button type="button" aria-label="Remove ${escapeHtml(p.label)}" data-remove="${p.id}">×</button></span>`
    )
    .join("");
  contextPinsEl.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      pinnedContexts = pinnedContexts.filter((p) => p.id !== btn.getAttribute("data-remove"));
      renderPins();
    });
  });
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setPinPicking(on) {
  pinPicking = on;
  document.body.classList.toggle("pin-picking", on);
  pinModeBtn.setAttribute("aria-pressed", String(on));
  pinBanner.hidden = !on;
  composeHint.textContent = on
    ? "Click a highlighted section to pin it. Multiple pins allowed."
    : "Pin Overview, Sync, Directive, or Settings sections, then Ask — or submit a journal entry for today’s directive.";
}

pinModeBtn.addEventListener("click", () => setPinPicking(!pinPicking));

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && pinPicking) setPinPicking(false);
});

document.addEventListener(
  "click",
  (event) => {
    if (!pinPicking) return;
    if (
      event.target.closest(
        "button, a, input, select, textarea, label, .pin-banner, .nav-jump, .actions, .context-pins"
      )
    ) {
      return;
    }
    const target = event.target.closest("[data-pin-id]");
    if (!target) return;
    event.preventDefault();
    event.stopPropagation();
    const id = target.getAttribute("data-pin-id");
    const label = target.getAttribute("data-pin-label") || id;
    const snippet = (target.innerText || "").replace(/\s+/g, " ").trim().slice(0, 480);
    if (!pinnedContexts.some((p) => p.id === id)) {
      pinnedContexts.push({ id, label, snippet });
      renderPins();
    }
    setPinPicking(false);
  },
  true
);

attachImgBtn.addEventListener("click", () => composeImage.click());

composeImage.addEventListener("change", () => {
  const file = composeImage.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    imageAttachment = { name: file.name, mime: file.type, data_url: reader.result };
    imagePreview.hidden = false;
    imagePreview.innerHTML =
      `<img src="${reader.result}" alt="attachment preview" />` +
      `<button type="button" id="clear-img" class="ghost">Clear image</button>`;
    document.getElementById("clear-img").onclick = () => {
      imageAttachment = null;
      imagePreview.hidden = true;
      imagePreview.innerHTML = "";
      composeImage.value = "";
    };
  };
  reader.readAsDataURL(file);
});

dictateBtn.addEventListener("click", () => {
  const Ctor = SpeechRecognitionCtor();
  if (!Ctor) {
    dictateStatus.hidden = false;
    dictateStatus.textContent = "Browser dictation not supported here. Type instead.";
    return;
  }
  if (!recognition) {
    recognition = new Ctor();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }
      textarea.value = transcript.trim();
      autosizeComposer();
    };
    recognition.onerror = () => {
      recognizing = false;
      dictateBtn.textContent = "Dictate";
      dictateStatus.hidden = false;
      dictateStatus.textContent = "Dictation stopped. You can keep typing.";
    };
    recognition.onend = async () => {
      recognizing = false;
      dictateBtn.textContent = "Dictate";
      const spoken = textarea.value.trim();
      if (isSyncCommand(spoken)) {
        dictateStatus.hidden = false;
        dictateStatus.textContent = "Voice sync command detected — syncing…";
        try {
          const { ok, n } = await runOnDemandSync("voice");
          dictateStatus.textContent = `Voice sync: ${ok}/${n} source(s) succeeded.`;
          await refreshDashboard();
        } catch (err) {
          dictateStatus.textContent = String(err);
        }
      }
    };
  }
  if (recognizing) {
    recognition.stop();
    return;
  }
  dictateStatus.hidden = false;
  dictateStatus.textContent = "Listening…";
  dictateBtn.textContent = "Stop";
  recognizing = true;
  recognition.start();
});

function showDirectivePayload(data) {
  directiveText.textContent = data.directive;
  disclaimerText.textContent = data.disclaimer || "";
  if (directiveMode) {
    const label =
      data.output_mode_label ||
      "Training planning — non-medical decision support (not diagnosis or treatment).";
    directiveMode.textContent = label;
    directiveMode.hidden = false;
  }
  const scores = data.scores || {};
  const selected = (data.signals && data.signals.selected) || [];
  const ev = data.evidence || {};
  if (selected.length) {
    scoreRow.innerHTML = selected
      .map((s) => {
        const value = s.score ?? "—";
        const label = s.label || String(s.id || "").replaceAll("_", " ");
        return `<span title="${(s.relevance || s.rationale || "").replaceAll('"', "&quot;")}">${label}<strong>${value}</strong></span>`;
      })
      .join("");
    scoreRow.style.gridTemplateColumns = `repeat(${Math.min(selected.length, 5)}, minmax(0, 1fr))`;
  } else {
    scoreRow.innerHTML = ["front_rack", "sleep", "diet", "workout_preparation", "overall"]
      .map((key) => {
        const value = scores[key]?.score ?? "—";
        const label = key.replaceAll("_", " ");
        return `<span>${label}<strong>${value}</strong></span>`;
      })
      .join("");
    scoreRow.style.gridTemplateColumns = "";
  }
  const wod = data.wod_decision || {};
  todayPre.textContent = JSON.stringify(
    {
      today: ev.today || data.intake,
      wod_decision: wod,
      macro_pool: scores.macro_pool,
      signals: data.signals,
    },
    null,
    2
  );
  historyPre.textContent = JSON.stringify(ev.history || [], null, 2);
  conflictsPre.textContent = JSON.stringify(ev.conflicts || [], null, 2);
  evidencePre.textContent = JSON.stringify(
    {
      extractor: data.extractor,
      log_id: data.log_id,
      resolution_policy: ev.resolution_policy,
      tts: data.tts,
      scores_note: ev.note,
      signals_selected: ev.signals_selected,
    },
    null,
    2
  );
  result.hidden = false;
  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function submitDirective() {
  const text = textarea.value.trim();
  if (!text) {
    composeHint.textContent = "Write a journal update before getting a directive.";
    return;
  }
  if (isSyncCommand(text)) {
    directiveBtn.disabled = true;
    try {
      const { ok, n } = await runOnDemandSync("voice");
      result.hidden = false;
      directiveText.textContent = `On-demand sync: ${ok}/${n} source(s) succeeded.`;
      disclaimerText.textContent =
        "Sync is a data refresh — not a training directive or medical advice.";
      await refreshDashboard();
    } catch (err) {
      result.hidden = false;
      directiveText.textContent = String(err);
    } finally {
      directiveBtn.disabled = false;
    }
    return;
  }

  directiveBtn.disabled = true;
  askBtn.disabled = true;
  directiveBtn.textContent = "Composing…";
  try {
    const res = await fetch("/api/directive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, speak: speakToggle.checked }),
    });
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
    const data = await res.json();
    showDirectivePayload(data);
    if (speakToggle.checked && "speechSynthesis" in window) {
      const utter = new SpeechSynthesisUtterance(data.directive);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }
    refreshDashboard();
  } catch (err) {
    directiveText.textContent = err.message || "Something went wrong.";
    disclaimerText.textContent = "";
    scoreRow.innerHTML = "";
    todayPre.textContent = "";
    historyPre.textContent = "";
    conflictsPre.textContent = "";
    evidencePre.textContent = "";
    result.hidden = false;
  } finally {
    directiveBtn.disabled = false;
    askBtn.disabled = false;
    directiveBtn.textContent = "Get directive";
  }
}

function appendBubble(role, content, opts = {}) {
  thread.hidden = false;
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  if (opts.modeLabel) {
    const tag = document.createElement("span");
    tag.className = "output-mode-tag";
    tag.textContent = opts.modeLabel;
    div.appendChild(tag);
  }
  if (opts.thumb) {
    const img = document.createElement("img");
    img.className = "thumb";
    img.src = opts.thumb;
    img.alt = "";
    const span = document.createElement("span");
    span.textContent = content;
    div.appendChild(img);
    div.appendChild(span);
  } else {
    const span = document.createElement("span");
    span.textContent = content;
    div.appendChild(span);
  }
  if (opts.pins?.length) {
    const meta = document.createElement("span");
    meta.className = "pins-used";
    meta.textContent = `Context: ${opts.pins.map((p) => p.label).join(", ")}`;
    div.appendChild(meta);
  }
  threadLog.appendChild(div);
  threadLog.scrollTop = threadLog.scrollHeight;
}

async function buildScreenContext() {
  const primary = pinnedContexts[0]?.id || "overview";
  const metric = document.getElementById("chart-metric")?.value || null;
  const params = new URLSearchParams({
    panel: primary,
    route: window.location.pathname + window.location.hash,
  });
  if (selectedGoalId) params.set("goal_id", selectedGoalId);
  if (metric) params.set("chart_metric", metric);
  if (typeof chartHorizon !== "undefined") params.set("horizon", chartHorizon);
  if (chatSessionId) params.set("session_id", chatSessionId);
  let screen = {};
  try {
    screen = await (await fetch(`/api/context/screen?${params}`)).json();
  } catch {
    screen = { panel: primary, route: window.location.pathname };
  }
  // Prefer typed fields from server; attach pins client-side
  screen.pins = pinnedContexts.map((p) => ({
    id: p.id,
    label: p.label,
    snippet: (p.snippet || "").slice(0, 240),
  }));
  screen.input = "composer";
  screen.selected_goal_id = selectedGoalId || screen.selected_goal_id || null;
  screen.selected_chart_metric = metric || screen.selected_chart_metric || null;
  screen.date_range = { horizon: typeof chartHorizon !== "undefined" ? chartHorizon : "month" };
  // Never send HTML blobs
  delete screen.html;
  delete screen.script;
  return screen;
}

async function submitAsk() {
  const message = textarea.value.trim();
  if (!message && !imageAttachment) {
    composeHint.textContent = "Type a question or attach an image before Ask.";
    return;
  }
  if (isSyncCommand(message)) {
    const { ok, n } = await runOnDemandSync("chat");
    appendBubble("user", message);
    appendBubble("assistant", `On-demand sync: ${ok}/${n} source(s) succeeded.`);
    await refreshDashboard();
    return;
  }

  const pinsSnapshot = [...pinnedContexts];
  const attachments = imageAttachment
    ? [{ name: imageAttachment.name, mime: imageAttachment.mime, preview: true }]
    : [];
  appendBubble("user", message || "(image)", {
    thumb: imageAttachment?.data_url,
    pins: pinsSnapshot,
  });

  askBtn.disabled = true;
  directiveBtn.disabled = true;
  askBtn.textContent = "Asking…";
  const sentThumb = imageAttachment?.data_url;
  imageAttachment = null;
  imagePreview.hidden = true;
  imagePreview.innerHTML = "";
  composeImage.value = "";

  try {
    const screen = await buildScreenContext();
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message || "Please review the attached image and pinned page context.",
        screen_context: screen,
        attachments,
        session_id: chatSessionId,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    chatSessionId = data.session_id || chatSessionId;
    if (chatSessionId) localStorage.setItem("aegis_chat_session_id", chatSessionId);
    appendBubble("assistant", data.reply, {
      modeLabel:
        data.output_mode_label ||
        "Health analysis — observational / non-prescriptive (not a care plan).",
    });
    if (data.chart_hints?.length) {
      document.getElementById("chart-metric").value = data.chart_hints[0];
      refreshChart();
    }
  } catch (err) {
    appendBubble("assistant", String(err));
  } finally {
    askBtn.disabled = false;
    directiveBtn.disabled = false;
    askBtn.textContent = "Ask";
  }
  void sentThumb;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitDirective();
});

askBtn.addEventListener("click", async () => {
  await submitAsk();
});

document.getElementById("chat-search-form")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const q = document.getElementById("chat-search-q").value.trim();
  const hitsEl = document.getElementById("chat-search-hits");
  if (!hitsEl) return;
  if (!q) {
    hitsEl.hidden = true;
    hitsEl.innerHTML = "";
    return;
  }
  try {
    const res = await fetch(`/api/chat/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const hits = data.hits || [];
    thread.hidden = false;
    if (!hits.length) {
      hitsEl.hidden = false;
      hitsEl.innerHTML = `<li class="hint">No matches.</li>`;
      return;
    }
    hitsEl.hidden = false;
    hitsEl.innerHTML = hits
      .map(
        (h) => `<li>
          <div class="hit-meta">${escapeHtml(h.role)} · ${escapeHtml(h.session_title || h.session_id)}</div>
          ${escapeHtml(h.snippet || h.content || "")}
        </li>`
      )
      .join("");
  } catch (err) {
    hitsEl.hidden = false;
    hitsEl.innerHTML = `<li class="hint">${String(err)}</li>`;
  }
});

async function restoreChatSession() {
  if (!chatSessionId || !threadLog) return;
  try {
    const res = await fetch(
      `/api/chat/history?session_id=${encodeURIComponent(chatSessionId)}&limit=40`
    );
    if (!res.ok) return;
    const data = await res.json();
    const msgs = data.messages || [];
    if (!msgs.length) return;
    thread.hidden = false;
    threadLog.innerHTML = "";
    for (const m of msgs) {
      appendBubble(m.role, m.content);
    }
  } catch {
    /* ignore restore errors */
  }
}

textarea.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    submitAsk();
  }
});

function fmtTime(ts) {
  if (!ts) return "never";
  try {
    return new Date(ts * 1000).toLocaleString();
  } catch {
    return String(ts);
  }
}

async function refreshSources() {
  const list = document.getElementById("source-list");
  const hint = document.getElementById("sync-hint");
  const fitbitStatus = document.getElementById("fitbit-status");
  const bgEnabled = document.getElementById("bg-sync-enabled");
  const bgInterval = document.getElementById("bg-sync-interval");
  const bgStatus = document.getElementById("bg-sync-status");
  try {
    const res = await fetch("/api/sources");
    const data = await res.json();
    const sources = data.sources || [];
    list.innerHTML = sources
      .map((s) => {
        const state = s.integration_state || s.mode || "unknown";
        const stale = s.stale ? " · stale" : "";
        const err = s.last_error ? ` · err: ${s.last_error.code}` : "";
        return `<li><strong>${s.label || s.source_id}</strong>
          <span>${s.enabled ? "on" : "off"} · ${state}${stale}${err}</span>
          <span class="muted">last ok: ${fmtTime(s.last_success_at)}</span></li>`;
      })
      .join("");
    const staleIds = data.stale || [];
    hint.textContent = staleIds.length
      ? `Stale sources: ${staleIds.join(", ")} — sync or wait for background tick.`
      : "No enabled sources marked stale.";
    const cfg = data.config || {};
    if (bgEnabled) bgEnabled.checked = !!cfg.background_enabled;
    if (bgInterval && cfg.interval_seconds) bgInterval.value = cfg.interval_seconds;
    try {
      const bgRes = await fetch("/api/sync/background");
      const bg = await bgRes.json();
      if (bgStatus) {
        bgStatus.textContent = bg.running
          ? `loop on · ticks=${bg.ticks || 0}`
          : "loop idle";
      }
    } catch {
      if (bgStatus) bgStatus.textContent = "";
    }
    const fitbit = sources.find((s) => s.source_id === "fitbit");
    if (fitbit) {
      fitbitStatus.textContent = `${fitbit.integration_state || "unknown"} — ${
        fitbit.detail || "OAuth not live in this build."
      } live_oauth=${fitbit.live_oauth === true}`;
    }
  } catch (err) {
    hint.textContent = err.message || "Could not load sources.";
  }
}

async function refreshEnvironment() {
  const pre = document.getElementById("env-pre");
  try {
    const res = await fetch("/api/environment");
    const data = await res.json();
    pre.textContent = JSON.stringify(
      {
        mode: data.mode,
        source: data.source,
        weather: data.weather,
        aqi: data.aqi,
        detail: data.detail,
      },
      null,
      2
    );
  } catch (err) {
    pre.textContent = String(err);
  }
}

async function refreshAlertsGoals() {
  const pre = document.getElementById("alerts-pre");
  try {
    const [alertsRes, goalsRes] = await Promise.all([
      fetch("/api/alerts"),
      fetch("/api/goals"),
    ]);
    const alerts = alertsRes.ok ? await alertsRes.json() : { error: alertsRes.status };
    const goals = goalsRes.ok ? await goalsRes.json() : { error: goalsRes.status };
    pre.textContent = JSON.stringify({ alerts, goals }, null, 2);
  } catch (err) {
    pre.textContent = String(err);
  }
}

let chartHorizon = "month";

function renderChart(spec, meta = {}) {
  const svg = document.getElementById("chart-svg");
  const note = document.getElementById("chart-note");
  const bandsEl = document.getElementById("chart-bands");
  const series = (spec.series && spec.series[0] && spec.series[0].points) || [];
  const missing = spec.missing || meta.missing || [];
  note.textContent =
    [
      spec.source_note,
      missing.length ? `Missing: ${missing.join(", ")}` : "",
      (meta.stale_sources || []).length
        ? `Stale: ${(meta.stale_sources || []).map((s) => s.source_id).join(", ")}`
        : "",
    ]
      .filter(Boolean)
      .join(" · ") || "";
  const bands = spec.goal_bands || meta.goal_bands || [];
  if (bandsEl) {
    bandsEl.textContent = bands.length
      ? "Goal bands: " +
        bands
          .map((b) => `${b.title || b.goal_id || b.metric}@${b.target}`)
          .join("; ")
      : "No goal bands for this metric.";
  }
  if (!series.length) {
    svg.innerHTML = `<text x="12" y="70" fill="#1a2421" font-size="12">No points for ${
      spec.metric || "metric"
    } (${chartHorizon})</text>`;
    return;
  }
  const ys = series.map((p) => Number(p.y));
  const bandYs = bands.map((b) => Number(b.target)).filter((n) => !Number.isNaN(n));
  const minY = Math.min(...ys, ...(bandYs.length ? bandYs : ys));
  const maxY = Math.max(...ys, ...(bandYs.length ? bandYs : ys));
  const pad = 12;
  const w = 320;
  const h = 140;
  const span = maxY - minY || 1;
  const coords = series.map((p, i) => {
    const x = pad + (i / Math.max(1, series.length - 1)) * (w - pad * 2);
    const y = h - pad - ((Number(p.y) - minY) / span) * (h - pad * 2);
    return `${x},${y}`;
  });
  const bandLines = bandYs
    .map((target) => {
      const y = h - pad - ((target - minY) / span) * (h - pad * 2);
      return `<line x1="${pad}" y1="${y}" x2="${w - pad}" y2="${y}" stroke="#c45c26" stroke-width="1.5" stroke-dasharray="4 3" />`;
    })
    .join("");
  svg.innerHTML = `
    ${bandLines}
    <polyline fill="none" stroke="#0f3d32" stroke-width="2"
      points="${coords.join(" ")}" />
    ${coords
      .map((c) => {
        const [x, y] = c.split(",");
        return `<circle cx="${x}" cy="${y}" r="2.5" fill="#c45c26" />`;
      })
      .join("")}
  `;
}

async function refreshChart() {
  const metric = document.getElementById("chart-metric").value;
  const explainEl = document.getElementById("chart-explain");
  if (explainEl) {
    explainEl.hidden = true;
    explainEl.textContent = "";
  }
  try {
    const res = await fetch(
      `/api/progress/${encodeURIComponent(metric)}?horizon=${encodeURIComponent(chartHorizon)}`
    );
    if (!res.ok) throw new Error(`progress ${res.status}`);
    const view = await res.json();
    renderChart(view.chart || view, view);
  } catch (err) {
    document.getElementById("chart-note").textContent = String(err);
  }
}

async function refreshDashboard() {
  await Promise.all([refreshSources(), refreshEnvironment(), refreshAlertsGoals(), refreshChart()]);
}

/* --- Goal Graph UI (GL3) --- */
let selectedGoalId = null;
let taskView = "inbox";
let goalFlatCache = [];

function flattenGoalTree(nodes, depth = 0, out = []) {
  for (const n of nodes || []) {
    out.push({ ...n.goal, depth });
    flattenGoalTree(n.children, depth + 1, out);
  }
  return out;
}

function renderGoalTreeNodes(nodes) {
  if (!nodes?.length) return `<li class="hint">No goals yet — add one below.</li>`;
  return nodes
    .map((n) => {
      const g = n.goal;
      const selected = g.id === selectedGoalId ? "is-selected" : "";
      const kids = n.children?.length
        ? `<ul>${renderGoalTreeNodes(n.children)}</ul>`
        : "";
      return `<li>
        <button type="button" class="goal-node ${selected}" data-goal-id="${g.id}">
          ${escapeHtml(g.title)}
          <span class="goal-meta">${escapeHtml(g.status)}${g.metric ? ` · ${escapeHtml(g.metric)}` : ""}</span>
        </button>
        ${kids}
      </li>`;
    })
    .join("");
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fillTaskGoalSelect() {
  const sel = document.getElementById("task-new-goal");
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = goalFlatCache
    .map(
      (g) =>
        `<option value="${g.id}">${"· ".repeat(g.depth || 0)}${escapeHtml(g.title)}</option>`
    )
    .join("");
  if (prev && goalFlatCache.some((g) => g.id === prev)) sel.value = prev;
  else if (selectedGoalId) sel.value = selectedGoalId;
}

function openGoalEditor(goal) {
  selectedGoalId = goal.id;
  document.getElementById("goal-editor-empty").hidden = true;
  const form = document.getElementById("goal-editor");
  form.hidden = false;
  document.getElementById("goal-edit-id").value = goal.id;
  document.getElementById("goal-edit-title").value = goal.title || "";
  document.getElementById("goal-edit-description").value = goal.description || "";
  document.getElementById("goal-edit-metric").value = goal.metric || "";
  document.getElementById("goal-edit-criteria").value = goal.success_criteria || "";
  document.getElementById("goal-editor-hint").textContent = "";
  document.querySelectorAll(".goal-node").forEach((btn) => {
    btn.classList.toggle("is-selected", btn.dataset.goalId === goal.id);
  });
  fillTaskGoalSelect();
}

async function refreshGoalTree() {
  const treeEl = document.getElementById("goal-tree");
  if (!treeEl) return;
  try {
    const res = await fetch("/api/goal-graph");
    if (!res.ok) throw new Error(`goal-graph ${res.status}`);
    const snap = await res.json();
    const tree = snap.goal_tree || [];
    goalFlatCache = flattenGoalTree(tree);
    treeEl.innerHTML = renderGoalTreeNodes(tree);
    fillTaskGoalSelect();
    if (selectedGoalId) {
      const g = goalFlatCache.find((x) => x.id === selectedGoalId);
      if (g) openGoalEditor(g);
    }
  } catch (err) {
    treeEl.innerHTML = `<li class="hint">${escapeHtml(String(err))}</li>`;
  }
}

async function refreshTaskList() {
  const list = document.getElementById("task-list");
  if (!list) return;
  try {
    const res = await fetch(`/api/goal-graph/tasks?view=${encodeURIComponent(taskView)}`);
    if (!res.ok) throw new Error(`tasks ${res.status}`);
    const data = await res.json();
    const tasks = data.tasks || [];
    if (!tasks.length) {
      list.innerHTML = `<li class="hint">No tasks in ${escapeHtml(taskView)}.</li>`;
      return;
    }
    list.innerHTML = tasks
      .map((t) => {
        const goal = goalFlatCache.find((g) => g.id === t.goal_id);
        return `<li data-task-id="${t.id}">
          <p class="task-title">${escapeHtml(t.title)}</p>
          <p class="task-meta">${escapeHtml(t.status)}${goal ? ` · ${escapeHtml(goal.title)}` : ""}${
            t.due_date ? ` · due ${escapeHtml(t.due_date)}` : ""
          }</p>
          ${
            t.status !== "completed"
              ? `<div class="hitl-actions">
                  <button type="button" class="ghost task-complete-btn" data-task-id="${t.id}">Mark done</button>
                </div>`
              : ""
          }
        </li>`;
      })
      .join("");
  } catch (err) {
    list.innerHTML = `<li class="hint">${escapeHtml(String(err))}</li>`;
  }
}

async function refreshSuggestions() {
  const list = document.getElementById("suggestion-list");
  if (!list) return;
  try {
    const res = await fetch("/api/goal-graph/suggestions?pending_only=true");
    if (!res.ok) throw new Error(`suggestions ${res.status}`);
    const data = await res.json();
    const items = data.suggestions || [];
    if (!items.length) {
      list.innerHTML = `<li class="hint">No pending suggestions.</li>`;
      return;
    }
    list.innerHTML = items
      .map((s) => {
        const evidence = (s.evidence || []).map(escapeHtml).join("; ") || "—";
        const assumptions = (s.assumptions || []).map(escapeHtml).join("; ") || "—";
        return `<li data-suggestion-id="${s.id}">
          <p class="sug-title">${escapeHtml(s.title)}</p>
          <p class="sug-meta">${escapeHtml(s.kind)} · confidence ${escapeHtml(s.confidence)} · ${escapeHtml(s.reason || "")}</p>
          <details>
            <summary>Evidence &amp; assumptions</summary>
            <p>Evidence: ${evidence}</p>
            <p>Assumptions: ${assumptions}</p>
          </details>
          <div class="hitl-actions">
            <button type="button" class="sug-decide" data-id="${s.id}" data-decision="approved">Approve</button>
            <button type="button" class="ghost sug-decide" data-id="${s.id}" data-decision="edited">Edit &amp; approve</button>
            <button type="button" class="ghost sug-decide" data-id="${s.id}" data-decision="rejected">Reject</button>
            <button type="button" class="ghost sug-decide" data-id="${s.id}" data-decision="deferred">Defer</button>
          </div>
        </li>`;
      })
      .join("");
  } catch (err) {
    list.innerHTML = `<li class="hint">${escapeHtml(String(err))}</li>`;
  }
}

async function refreshGoalsUi() {
  await refreshGoalTree();
  await Promise.all([refreshTaskList(), refreshSuggestions()]);
}

document.getElementById("goal-tree")?.addEventListener("click", (ev) => {
  const btn = ev.target.closest(".goal-node");
  if (!btn) return;
  const g = goalFlatCache.find((x) => x.id === btn.dataset.goalId);
  if (g) openGoalEditor(g);
});

document.getElementById("goal-create-form")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const title = document.getElementById("goal-new-title").value.trim();
  const metric = document.getElementById("goal-new-metric").value.trim();
  if (!title) return;
  const res = await fetch("/api/goal-graph/goals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, metric: metric || null }),
  });
  if (!res.ok) {
    document.getElementById("goal-editor-hint").textContent = `Create failed ${res.status}`;
    return;
  }
  document.getElementById("goal-new-title").value = "";
  document.getElementById("goal-new-metric").value = "";
  await refreshGoalsUi();
});

document.getElementById("goal-editor")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const id = document.getElementById("goal-edit-id").value;
  const hint = document.getElementById("goal-editor-hint");
  const body = {
    title: document.getElementById("goal-edit-title").value.trim(),
    description: document.getElementById("goal-edit-description").value.trim(),
    metric: document.getElementById("goal-edit-metric").value.trim() || null,
    success_criteria: document.getElementById("goal-edit-criteria").value.trim() || null,
  };
  const res = await fetch(`/api/goal-graph/goals/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  hint.textContent = res.ok ? "Saved." : `Save failed ${res.status}`;
  if (res.ok) await refreshGoalTree();
});

document.getElementById("goal-archive-btn")?.addEventListener("click", async () => {
  const id = document.getElementById("goal-edit-id").value;
  if (!id || !confirm("Archive this goal?")) return;
  const res = await fetch(`/api/goal-graph/goals/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "abandoned" }),
  });
  document.getElementById("goal-editor-hint").textContent = res.ok
    ? "Archived."
    : `Archive failed ${res.status}`;
  if (res.ok) {
    selectedGoalId = null;
    document.getElementById("goal-editor").hidden = true;
    document.getElementById("goal-editor-empty").hidden = false;
    await refreshGoalsUi();
  }
});

document.querySelectorAll(".task-view").forEach((btn) => {
  btn.addEventListener("click", async () => {
    taskView = btn.dataset.view;
    document.querySelectorAll(".task-view").forEach((b) => {
      const on = b === btn;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    await refreshTaskList();
  });
});

document.getElementById("task-create-form")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const title = document.getElementById("task-new-title").value.trim();
  const goal_id = document.getElementById("task-new-goal").value;
  if (!title || !goal_id) return;
  const res = await fetch("/api/goal-graph/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, goal_id, status: "inbox" }),
  });
  if (res.ok) {
    document.getElementById("task-new-title").value = "";
    taskView = "inbox";
    document.querySelectorAll(".task-view").forEach((b) => {
      const on = b.dataset.view === "inbox";
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    await refreshTaskList();
  }
});

document.getElementById("task-list")?.addEventListener("click", async (ev) => {
  const btn = ev.target.closest(".task-complete-btn");
  if (!btn) return;
  await fetch(`/api/goal-graph/tasks/${encodeURIComponent(btn.dataset.taskId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "completed" }),
  });
  await refreshTaskList();
});

document.getElementById("suggestion-list")?.addEventListener("click", async (ev) => {
  const btn = ev.target.closest(".sug-decide");
  if (!btn) return;
  const id = btn.dataset.id;
  const decision = btn.dataset.decision;
  let edited_payload = null;
  if (decision === "edited") {
    const title = prompt("Edited task title (required):");
    if (!title) return;
    edited_payload = { title, description: "Edited in suggestion review" };
  }
  const res = await fetch(`/api/goal-graph/suggestions/${encodeURIComponent(id)}/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      decision: decision === "edited" ? "approved" : decision,
      edited_payload,
    }),
  });
  if (!res.ok) {
    console.warn("decide failed", res.status);
    return;
  }
  await Promise.all([refreshSuggestions(), refreshTaskList()]);
});

document.getElementById("goal-refresh-btn")?.addEventListener("click", refreshGoalsUi);
document.getElementById("suggestion-refresh-btn")?.addEventListener("click", refreshSuggestions);

document.getElementById("bg-sync-save").addEventListener("click", async () => {
  const hint = document.getElementById("sync-hint");
  const enabled = document.getElementById("bg-sync-enabled").checked;
  const interval = Number(document.getElementById("bg-sync-interval").value) || 3600;
  hint.textContent = "Saving sync config…";
  try {
    const res = await fetch("/api/sync/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        background_enabled: enabled,
        interval_seconds: Math.max(5, interval),
        sources: {},
        max_retries: 3,
        retry_backoff_seconds: 2,
      }),
    });
    if (!res.ok) throw new Error(`config ${res.status}`);
    hint.textContent = enabled
      ? `Background sync enabled every ${Math.max(5, interval)}s.`
      : "Background sync disabled (on-demand still works).";
    await refreshSources();
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("sync-now-btn").addEventListener("click", async () => {
  const hint = document.getElementById("sync-hint");
  hint.textContent = "Syncing…";
  try {
    const { ok, n } = await runOnDemandSync("button");
    hint.textContent = `Synced ${ok}/${n} source(s).`;
    await refreshDashboard();
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("chart-metric").addEventListener("change", refreshChart);

document.querySelectorAll(".horizon-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    chartHorizon = btn.dataset.horizon;
    document.querySelectorAll(".horizon-btn").forEach((b) => {
      b.classList.toggle("is-active", b === btn);
    });
    await refreshChart();
  });
});

document.getElementById("chart-explain-btn")?.addEventListener("click", async () => {
  const metric = document.getElementById("chart-metric").value;
  const el = document.getElementById("chart-explain");
  try {
    const res = await fetch(
      `/api/progress/${encodeURIComponent(metric)}/explain?horizon=${encodeURIComponent(chartHorizon)}`,
      { method: "POST" }
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    el.hidden = false;
    el.textContent = data.explanation || "";
  } catch (err) {
    el.hidden = false;
    el.textContent = String(err);
  }
});

document.getElementById("chart-task-btn")?.addEventListener("click", async () => {
  const metric = document.getElementById("chart-metric").value;
  const hint = document.getElementById("chart-task-hint");
  try {
    const res = await fetch(`/api/progress/${encodeURIComponent(metric)}/create-task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ horizon: chartHorizon }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    hint.textContent = data.detail || "Suggestion pending approval.";
    await refreshSuggestions();
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("fitbit-fixture-btn").addEventListener("click", async () => {
  const el = document.getElementById("fitbit-status");
  el.textContent = "Running fixture sync…";
  try {
    await fetch("/api/sources/fitbit/enable", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: true }),
    });
    const res = await fetch("/api/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: "fitbit", force: true }),
    });
    const data = await res.json();
    el.textContent = JSON.stringify(data.results?.[0] || data, null, 0).slice(0, 240);
    await refreshDashboard();
  } catch (err) {
    el.textContent = String(err);
  }
});

document.getElementById("fitbit-auth-btn").addEventListener("click", async () => {
  const el = document.getElementById("fitbit-status");
  try {
    const res = await fetch("/api/fitbit/status");
    const data = await res.json();
    el.textContent = `${data.integration_state}: ${data.detail}` +
      (data.auth_url ? ` auth_url=${data.auth_url}` : "");
  } catch (err) {
    el.textContent = String(err);
  }
});

document.getElementById("fitindex-ocr-btn").addEventListener("click", async () => {
  const hint = document.getElementById("fitindex-ocr-hint");
  const fileInput = document.getElementById("fitindex-ocr-file");
  if (!fileInput.files?.length) {
    hint.textContent = "Choose an image first.";
    return;
  }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  try {
    const res = await fetch("/api/fitindex/ocr", { method: "POST", body: fd });
    const data = await res.json();
    if (!data.ok) {
      hint.textContent = data.detail || "OCR unavailable";
      return;
    }
    hint.textContent = "OCR draft ready — review and confirm below.";
    showFitindexDraft(data.draft);
  } catch (err) {
    hint.textContent = String(err);
  }
});

function showFitindexDraft(draft) {
  const panel = document.getElementById("fitindex-draft");
  if (!panel || !draft) return;
  const proposed = draft.proposed || {};
  document.getElementById("fitindex-draft-id").value = draft.draft_id || "";
  document.getElementById("fitindex-edit-weight").value =
    proposed.weight_kg ?? "";
  document.getElementById("fitindex-edit-bf").value =
    proposed.body_fat_pct ?? "";
  document.getElementById("fitindex-edit-day").value = proposed.day || "";
  document.getElementById("fitindex-edit-notes").value = proposed.notes || "";
  panel.hidden = false;
  document.getElementById("fitindex-review-hint").textContent =
    "Edit if needed, then Confirm save. Nothing is stored until you confirm.";
  document.getElementById("fitindex-hint").textContent =
    `Draft ${draft.draft_id} ready for review.`;
}

function clearFitindexDraft() {
  const panel = document.getElementById("fitindex-draft");
  if (panel) panel.hidden = true;
  document.getElementById("fitindex-draft-id").value = "";
}

document.getElementById("fitindex-upload-btn").addEventListener("click", async () => {
  const hint = document.getElementById("fitindex-hint");
  const csv = document.getElementById("fitindex-csv").value;
  try {
    const res = await fetch("/api/fitindex/csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    showFitindexDraft(data);
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("fitindex-manual-btn")?.addEventListener("click", async () => {
  const hint = document.getElementById("fitindex-hint");
  const weight = document.getElementById("fitindex-manual-weight").value;
  const bf = document.getElementById("fitindex-manual-bf").value;
  try {
    const res = await fetch("/api/fitindex/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        weight_kg: weight === "" ? null : Number(weight),
        body_fat_pct: bf === "" ? null : Number(bf),
        notes: "manual_ui",
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    showFitindexDraft(data);
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("fitindex-confirm-btn")?.addEventListener("click", async () => {
  const hint = document.getElementById("fitindex-review-hint");
  const draftId = document.getElementById("fitindex-draft-id").value;
  if (!draftId) {
    hint.textContent = "No draft to confirm.";
    return;
  }
  const body = {
    confirmed: true,
    weight_kg: Number(document.getElementById("fitindex-edit-weight").value) || null,
    body_fat_pct: Number(document.getElementById("fitindex-edit-bf").value) || null,
    day: document.getElementById("fitindex-edit-day").value.trim() || null,
    notes: document.getElementById("fitindex-edit-notes").value.trim() || null,
  };
  try {
    const res = await fetch(`/api/fitindex/confirm/${encodeURIComponent(draftId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    hint.textContent = `Saved: ${(data.written || []).join(", ") || "ok"}`;
    clearFitindexDraft();
    document.getElementById("fitindex-hint").textContent = "Confirmed and saved.";
    await refreshDashboard();
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("fitindex-discard-btn")?.addEventListener("click", async () => {
  const hint = document.getElementById("fitindex-review-hint");
  const draftId = document.getElementById("fitindex-draft-id").value;
  if (!draftId) {
    clearFitindexDraft();
    return;
  }
  try {
    await fetch(`/api/fitindex/discard/${encodeURIComponent(draftId)}`, { method: "POST" });
  } catch (_) {
    /* ignore network */
  }
  clearFitindexDraft();
  document.getElementById("fitindex-hint").textContent = "Draft discarded.";
  hint.textContent = "";
});

function showTakeoutSummary(data, phase) {
  const panel = document.getElementById("takeout-summary");
  const body = document.getElementById("takeout-summary-body");
  if (!panel || !body) return;
  const prov = data.provenance || {};
  const lines = [
    `Phase: ${phase}`,
    `Mode: ${data.mode || "—"}`,
    `Primary metric path: ${prov.primary_metric_path ? "yes" : "no"}`,
    `Source: ${prov.source || "takeout"}`,
    `Quality: ${prov.quality || data.quality || "—"}`,
    `Files parsed: ${data.files_parsed ?? 0}`,
    `Metrics: ${(data.metrics || []).join(", ") || "—"}`,
    phase === "preview"
      ? `Would write: ${data.would_write ?? 0} points`
      : `Written: ${data.written ?? 0} points`,
  ];
  if ((data.sample || []).length) {
    lines.push("Sample:");
    for (const row of data.sample.slice(0, 5)) {
      lines.push(
        `  · ${row.metric}${row.value != null ? "=" + row.value : ""} (${row.day || row.file || ""})`
      );
    }
  }
  body.textContent = lines.join("\n");
  panel.hidden = false;
}

document.getElementById("takeout-preview-btn")?.addEventListener("click", async () => {
  const hint = document.getElementById("takeout-hint");
  const fileInput = document.getElementById("takeout-file");
  if (!fileInput.files?.length) {
    hint.textContent = "Choose a .zip first.";
    return;
  }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  try {
    const res = await fetch("/api/takeout/preview", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    hint.textContent = "Preview only — nothing written yet. Confirm import to save.";
    showTakeoutSummary(data, "preview");
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("takeout-upload-btn").addEventListener("click", async () => {
  const hint = document.getElementById("takeout-hint");
  const fileInput = document.getElementById("takeout-file");
  if (!fileInput.files?.length) {
    hint.textContent = "Choose a .zip first.";
    return;
  }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  try {
    const res = await fetch("/api/takeout/zip", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    hint.textContent = `Imported ${data.written} points (${(data.metrics || []).join(", ")}).`;
    showTakeoutSummary(data, "confirmed");
    await refreshDashboard();
  } catch (err) {
    hint.textContent = String(err);
  }
});

document.getElementById("manual-btn").addEventListener("click", async () => {
  const hint = document.getElementById("manual-hint");
  const metric = document.getElementById("manual-metric").value.trim();
  const value = Number(document.getElementById("manual-value").value);
  try {
    const res = await fetch("/api/metrics/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metric, value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    hint.textContent = `Logged ${data.metric}=${data.value}`;
    await refreshDashboard();
  } catch (err) {
    hint.textContent = String(err);
  }
});

refreshDashboard();
refreshGoalsUi();
restoreChatSession();

async function refreshGeoStatus() {
  const el = document.getElementById("geo-status");
  const toggle = document.getElementById("geo-consent-toggle");
  if (!el) return;
  try {
    const res = await fetch("/api/geo/status");
    const data = await res.json();
    el.textContent = `${data.enabled ? "enabled" : "disabled"} · cloud_llm=${data.cloud_llm} · ${data.detail || ""}`;
    if (toggle) toggle.checked = !!data.enabled;
  } catch (err) {
    el.textContent = String(err);
  }
}

document.getElementById("geo-consent-toggle")?.addEventListener("change", async (ev) => {
  const enabled = ev.target.checked;
  const el = document.getElementById("geo-status");
  try {
    const res = await fetch("/api/geo/consent", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    el.textContent = `${data.enabled ? "enabled" : "disabled"} · ${data.detail || ""}`;
  } catch (err) {
    ev.target.checked = !enabled;
    el.textContent = String(err);
  }
});

document.getElementById("geo-revoke-btn")?.addEventListener("click", async () => {
  const toggle = document.getElementById("geo-consent-toggle");
  const el = document.getElementById("geo-status");
  try {
    const res = await fetch("/api/geo/consent", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: false }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    if (toggle) toggle.checked = false;
    el.textContent = `${data.enabled ? "enabled" : "disabled"} · ${data.detail || ""}`;
  } catch (err) {
    if (el) el.textContent = String(err);
  }
});

refreshGeoStatus();
