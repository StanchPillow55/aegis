const form = document.getElementById("update-form");
const textarea = document.getElementById("update-text");
const submitBtn = document.getElementById("submit-btn");
const dictateBtn = document.getElementById("dictate-btn");
const dictateStatus = document.getElementById("dictate-status");
const speakToggle = document.getElementById("speak-toggle");
const result = document.getElementById("result");
const directiveText = document.getElementById("directive-text");
const disclaimerText = document.getElementById("disclaimer-text");
const scoreRow = document.getElementById("score-row");
const todayPre = document.getElementById("today-pre");
const historyPre = document.getElementById("history-pre");
const conflictsPre = document.getElementById("conflicts-pre");
const evidencePre = document.getElementById("evidence-pre");

let recognizing = false;
let recognition = null;
let chatAttachment = null;

function SpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

dictateBtn.addEventListener("click", () => {
  const Ctor = SpeechRecognitionCtor();
  if (!Ctor) {
    dictateStatus.hidden = false;
    dictateStatus.textContent = "Browser dictation not supported here. Type your update instead.";
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
    };
    recognition.onerror = () => {
      recognizing = false;
      dictateBtn.textContent = "Dictate";
      dictateStatus.hidden = false;
      dictateStatus.textContent = "Dictation stopped. You can keep typing.";
    };
    recognition.onend = () => {
      recognizing = false;
      dictateBtn.textContent = "Dictate";
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = textarea.value.trim();
  if (!text) return;

  submitBtn.disabled = true;
  submitBtn.textContent = "Composing…";
  try {
    const res = await fetch("/api/directive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, speak: speakToggle.checked }),
    });
    if (!res.ok) {
      throw new Error(`Request failed (${res.status})`);
    }
    const data = await res.json();
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
    submitBtn.disabled = false;
    submitBtn.textContent = "Get directive";
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
      ? `Stale sources: ${staleIds.join(", ")}`
      : "No enabled sources marked stale.";
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

document.getElementById("sync-now-btn").addEventListener("click", async () => {
  const hint = document.getElementById("sync-hint");
  hint.textContent = "Syncing…";
  try {
    const res = await fetch("/api/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force: false }),
    });
    const data = await res.json();
    hint.textContent = `Synced ${((data.results || []).length)} source(s).`;
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

/* Chat dock */
const chatToggle = document.getElementById("chat-toggle");
const chatPanel = document.getElementById("chat-panel");
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatPreview = document.getElementById("chat-preview");
const chatImage = document.getElementById("chat-image");

chatToggle.addEventListener("click", () => {
  const open = chatPanel.hidden;
  chatPanel.hidden = !open;
  chatToggle.setAttribute("aria-expanded", String(open));
});

document.getElementById("chat-attach").addEventListener("click", () => chatImage.click());

chatImage.addEventListener("change", () => {
  const file = chatImage.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    chatAttachment = {
      name: file.name,
      mime: file.type,
      data_url: reader.result,
    };
    chatPreview.hidden = false;
    chatPreview.innerHTML = `<img src="${reader.result}" alt="preview" /><button type="button" id="chat-clear-img" class="ghost">Clear</button>`;
    document.getElementById("chat-clear-img").onclick = () => {
      chatAttachment = null;
      chatPreview.hidden = true;
      chatPreview.innerHTML = "";
      chatImage.value = "";
    };
  };
  reader.readAsDataURL(file);
});

function appendChatBubble(role, content, thumb) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  if (thumb) {
    div.innerHTML = `<img class="thumb" src="${thumb}" alt="" /><span></span>`;
    div.querySelector("span").textContent = content;
  } else {
    div.textContent = content;
  }
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message && !chatAttachment) return;
  const attachments = chatAttachment
    ? [{ name: chatAttachment.name, mime: chatAttachment.mime, preview: true }]
    : [];
  appendChatBubble("user", message || "(image)", chatAttachment?.data_url);
  chatInput.value = "";
  const sentThumb = chatAttachment?.data_url;
  chatAttachment = null;
  chatPreview.hidden = true;
  chatPreview.innerHTML = "";
  chatImage.value = "";
  try {
    const screen = await (await fetch("/api/context/screen")).json();
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message || "Please review the attached image.",
        screen_context: screen,
        attachments,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    appendChatBubble("assistant", data.reply);
    if (data.chart_hints?.length) {
      document.getElementById("chart-metric").value = data.chart_hints[0];
      refreshChart();
    }
  } catch (err) {
    appendChatBubble("assistant", String(err));
  }
  void sentThumb;
});

refreshDashboard();
