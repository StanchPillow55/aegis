# Tailscale remote access (security posture)

Aegis is designed to run on a home Apple Silicon M2 host with **local** SQLite and Ollama.

## Allowed exposure

| Surface | How |
|---|---|
| PWA / frontend | Tailscale **Serve** (mesh) to your devices. Optional Funnel only via auth-aware reverse proxy. |
| API (`/api/*`) | Same host through local reverse proxy with session/token auth. |
| SQLite / Ollama | **localhost only** — never Funnel targets, never public ports. |

## Forbidden

- Public Funnel directly to `uvicorn` without auth
- Exposing SQLite files or Ollama (`11434`) on Tailscale Funnel
- Shipping API keys in the frontend bundle

## Suggested topology

```
iPhone PWA  --Tailscale-->  reverse proxy (auth)  -->  127.0.0.1:8000 (FastAPI)
                                              \-->  (no path to Ollama/SQLite)
```

This document satisfies the Tailscale security specification checkpoint; live mesh setup remains operator-owned on the home Mac.
