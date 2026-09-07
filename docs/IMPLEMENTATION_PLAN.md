## Implementation Plan — Aegis Health Data Pipeline & Coach Interface

### Problem Statement

Aegis currently ingests health data only through manual daily voice/text check-ins. The goal is to expand it into a comprehensive personal health copilot by: (1) automatically ingesting continuous biometric time-series from Fitbit, body composition from FITINDEX, and lifestyle context from Google Calendar, (2) making the LLM fully aware of and able to query/display this data, (3) providing a conversational + visual dashboard interface accessible from home (full) and remotely (lightweight), and (4) supporting a full goal-tracking and planning system where the AI monitors progress, detects goal completion, and visualizes targets on charts.

### Requirements

**Data Ingestion:**
- Fitbit Web API (primary): HR, HRV, resting HR, SpO2, sleep, steps, distance, active minutes, calories, body weight/fat, stress score, breathing rate, activities
- FITINDEX: CSV file drop, screenshot OCR, or manual text entry for body composition
- Google Calendar API: event name, location, description for lifestyle context
- Geolocation: opt-in device location for environmental context (weather/AQI)
- File drop + text box for manual entry
- Fallback: Google Health Takeout export when Google Fit REST is fully sunset

**Sync Behavior:**
- Hybrid: automatic background sync on configurable schedule, toggleable per-source
- On-demand pull via button/voice

**LLM Awareness:**
- Full context: LLM knows what data exists, can query it, reason across sources, cross-reference conversation history
- Displays relevant charts/data inline in conversation
- Factual/observational only — reports trends, doesn't prescribe
- Goal-aware: frames data relative to explicit user-set goals, detects potential completion, asks for confirmation

**Safety & Alerts:**
- System provides recommended defaults (HR > 200bpm, SpO2 < 90%, resting HR +15% above baseline, HRV -30% below baseline)
- Dad can override any threshold or create custom alerts on any metric
- Critical alerts surface prominently in UI and LLM mentions them proactively
- Data staleness warnings (>24h since last sync per source)
- No medical diagnosis or prescription

**Goal Planning System:**
- Goals can be created manually (UI form) or extracted from conversation ("I want to get my body fat under 20%")
- Each goal has: metric, target value, direction, timeframe (optional), success criteria
- Goals show as reference lines/bands on dashboard charts where applicable
- AI cross-references health data + conversation data to track progress
- When AI detects goal completion → surfaces it to dad, asks for confirmation
- Dad can also manually check off goals
- Goal history preserved (completed, abandoned, in-progress)

**Interface:**
- Grafana-style interactive dashboard with clickable charts, goal lines overlaid
- Floating chat interface (text input, optional STT toggle via Web Speech API)
- Conversation history saved and searchable
- Accessible on Mac (full experience) and remotely via phone/browser

**Deployment:**
- Runs on Mac at home (M2) — full LLM + all services local
- Remote access via Tailscale Funnel for phone/browser (API proxy only)
- PWA installable on iPhone

### Task Breakdown

*(Tasks 1-15 omitted for brevity in this specific file, see original prompt for full breakdown)*
