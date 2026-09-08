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
let chatSessionId = null;

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
  const scores = data.scores || {};
  const ev = data.evidence || {};
  scoreRow.innerHTML = ["front_rack", "sleep", "diet", "workout_preparation", "overall"]
    .map((key) => {
      const value = scores[key]?.score ?? "—";
      const label = key.replaceAll("_", " ");
      return `<span>${label}<strong>${value}</strong></span>`;
    })
    .join("");
  const wod = data.wod_decision || {};
  todayPre.textContent = JSON.stringify(
    { today: ev.today || data.intake, wod_decision: wod, macro_pool: scores.macro_pool },
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
  if (opts.thumb) {
    div.innerHTML = `<img class="thumb" src="${opts.thumb}" alt="" /><span></span>`;
    div.querySelector("span").textContent = content;
  } else {
    div.textContent = content;
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
  let screen = {};
  try {
    screen = await (await fetch(`/api/context/screen?panel=${encodeURIComponent(primary)}`)).json();
  } catch {
    screen = { panel: primary };
  }
  screen.pinned = pinnedContexts.map((p) => ({
    id: p.id,
    label: p.label,
    snippet: p.snippet,
  }));
  screen.input = "composer";
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
    appendBubble("assistant", data.reply);
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

function renderChart(spec) {
  const svg = document.getElementById("chart-svg");
  const note = document.getElementById("chart-note");
  const series = (spec.series && spec.series[0] && spec.series[0].points) || [];
  note.textContent = spec.source_note || (spec.missing || []).join(", ") || "";
  if (!series.length) {
    svg.innerHTML = `<text x="12" y="60" fill="#1a2421" font-size="12">No points for ${
      spec.metric || "metric"
    }</text>`;
    return;
  }
  const ys = series.map((p) => Number(p.y));
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const pad = 12;
  const w = 320;
  const h = 120;
  const span = maxY - minY || 1;
  const coords = series.map((p, i) => {
    const x = pad + (i / Math.max(1, series.length - 1)) * (w - pad * 2);
    const y = h - pad - ((Number(p.y) - minY) / span) * (h - pad * 2);
    return `${x},${y}`;
  });
  svg.innerHTML = `
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
  try {
    const res = await fetch(`/api/charts/${encodeURIComponent(metric)}`);
    if (!res.ok) throw new Error(`chart ${res.status}`);
    renderChart(await res.json());
  } catch (err) {
    document.getElementById("chart-note").textContent = String(err);
  }
}

async function refreshDashboard() {
  await Promise.all([refreshSources(), refreshEnvironment(), refreshAlertsGoals(), refreshChart()]);
}

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
    hint.textContent = `Draft ${data.draft?.draft_id} — confirm via API before save.`;
  } catch (err) {
    hint.textContent = String(err);
  }
});

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
    hint.textContent = `Draft ${data.draft_id || "ok"} — confirm via API before save.`;
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
    hint.textContent = `Wrote ${data.written} points (${(data.metrics || []).join(", ")}).`;
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
