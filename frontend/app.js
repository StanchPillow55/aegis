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
    // Transitional labels until canonical four-score UI lands.
    scoreRow.innerHTML = ["readiness", "sleep", "soreness", "diet"]
      .map((key) => {
        const value = scores[key]?.score ?? "—";
        return `<span>${key}<strong>${value}</strong></span>`;
      })
      .join("");
    const ev = data.evidence || {};
    todayPre.textContent = JSON.stringify(ev.today || data.intake, null, 2);
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
