# Bug Spec — Localhost browser cannot reach running Aegis (`ERR_CONNECTION_REFUSED`)

**ID:** BUG-LOCALHOST-01  
**Severity:** High (blocks all browser demos / UI verification)  
**Status:** Diagnosed  
**Date:** 2026-09-07  
**Reporter evidence:** Chrome screenshot — “This site can’t be reached / 127.0.0.1 refused to connect / `ERR_CONNECTION_REFUSED`”  
**Environment:** Cursor Cloud Agent VM + user’s local Chrome

---

## 1. Symptom

| What the user sees | What the terminal shows |
|---|---|
| Browser: `ERR_CONNECTION_REFUSED` on `127.0.0.1` | `make os-dev` → `Uvicorn running on http://127.0.0.1:8000` |

The app **appears** started, but the browser cannot load the UI.

---

## 2. Diagnosis (verified)

### 2.1 Facts gathered on the agent host

```text
$ make os-dev
Uvicorn running on http://127.0.0.1:8000

$ ss -tlnp | grep 8000
LISTEN  127.0.0.1:8000  ... python3 (uvicorn)

$ curl -sS http://127.0.0.1:8000/health
{"status":"ok","mode":"open-source-foundation",...}

$ curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
200

$ curl -sS http://127.0.0.1/     # default port 80
Failed to connect ... port 80 ... Connection refused
```

**Conclusion:** On the machine where uvicorn runs, port **8000** is healthy. Port **80** is not.

### 2.2 Root cause analysis

There are **two independent failure modes**. Either alone produces the screenshot; both can stack.

#### RC-A — Loopback topology mismatch (primary for Cloud Agents)

`127.0.0.1` always means **this computer**.

| Process | Where it runs | What `127.0.0.1` means |
|---|---|---|
| `uvicorn` / `make os-dev` | Cursor **Cloud Agent VM** | The VM’s loopback |
| Chrome | User’s **laptop / desktop** | The laptop’s loopback |

The server is listening on the VM. The browser is asking the laptop. Nothing is listening on the laptop → **`ERR_CONNECTION_REFUSED`**.

This is not an application crash. The terminal is truthful; the browser is talking to a different host.

#### RC-B — Wrong port (likely co-factor in the screenshot)

Chrome’s copy for a refused connection often renders as:

> **127.0.0.1** refused to connect.

When the URL is `http://127.0.0.1/` (implicit **:80**), the port is frequently omitted from that headline.  
When the URL is `http://127.0.0.1:8000/`, Chrome usually includes `:8000` in the refuse line.

The provided screenshot matches the **port-80 / bare host** phrasing more closely than the `:8000` phrasing. Even on the VM, nothing listens on `:80`.

#### RC-C — Bind address too narrow (secondary / future tunnel)

`Makefile` currently starts:

```make
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Binding `127.0.0.1` is correct for same-machine local Mac demos, but it **rejects non-loopback clients**. Any future port-forward / Tailscale Serve / reverse-proxy path that hits the process via a non-loopback interface will still fail unless the app listens on `0.0.0.0` (or a specific Tailscale IP) behind an auth-aware proxy.

---

## 3. Non-causes (ruled out)

| Hypothesis | Why ruled out |
|---|---|
| App failed to boot | uvicorn logs “running”; curl `/health` → `ok` |
| FastAPI routing bug | `/` returns HTML 200; `/health` JSON 200 |
| Firewall on VM blocking local curl | Loopback curl succeeds |
| Missing frontend files | `/` returns `frontend/index.html` content |
| CORS | Connection never establishes; CORS is post-TCP |

---

## 4. Expected vs actual behavior

| Actor | Expected | Actual |
|---|---|---|
| Developer on **same host** as uvicorn | `http://127.0.0.1:8000` works | Works (verified via curl on agent) |
| Developer on **laptop** while uvicorn is on **Cloud Agent** | Must use a published URL / tunnel / remote desktop — **not** laptop `127.0.0.1` | Laptop Chrome → refused |
| Any client hitting bare `http://127.0.0.1/` | Should fail (nothing on :80) unless a proxy is added | Refused (verified) |

---

## 5. Detailed fixes

### Fix F1 — Document Cloud vs local browser topology (required)

Update `README.md` Quickstart with an explicit callout:

1. If `make os-dev` runs **inside a Cloud Agent / remote VM**, opening `127.0.0.1` in your **local** Chrome will always fail.
2. Use one of:
   - Run `make os-dev` on the **same machine** as the browser (Apple Silicon M2 host), then open `http://127.0.0.1:8000`
   - Or use Cursor’s port-forward / preview affordance **if available** for the agent
   - Or Tailscale Serve to the home Mac (see `docs/TAILSCALE.md`) — never raw public Funnel to uvicorn

### Fix F2 — Always print the full URL including `:8000`

Change `os-dev` to echo:

```text
Open http://127.0.0.1:8000/  (must include port 8000)
If the server is remote, 127.0.0.1 in YOUR browser is the wrong host.
```

### Fix F3 — Makefile bind strategy

Introduce an explicit host variable:

```make
DEV_HOST ?= 127.0.0.1
DEV_PORT ?= 8000
os-dev:
	@echo "Listening on http://$(DEV_HOST):$(DEV_PORT)/"
	@echo "Same-machine browser only for 127.0.0.1. Use DEV_HOST=0.0.0.0 for tunnels."
	python3 -m uvicorn backend.main:app --host $(DEV_HOST) --port $(DEV_PORT) --reload
```

- Default stays `127.0.0.1` (safer for local-only).
- Operators enabling Tailscale/proxy use `DEV_HOST=0.0.0.0` **behind auth**, per Tailscale spec.

### Fix F4 — Optional local `:80` redirect helper (nice-to-have, not required)

Do **not** run the app as root on :80 by default. Prefer:

- Document “must use `:8000`”
- Or a tiny user-space redirect only in local-dev compose later

### Fix F5 — Healthcheck target for “is the server up on this host?”

```make
os-health:
	curl -fsS http://127.0.0.1:$(DEV_PORT)/health | python3 -m json.tool
```

If `os-health` passes in the **same shell/host** as `os-dev` but the laptop browser fails → topology mismatch confirmed (RC-A).

### Fix F6 — Bug regression checklist (manual)

1. On server host: `make os-dev` + `make os-health` → pass  
2. On server host browser / curl: `http://127.0.0.1:8000/` → 200  
3. On laptop while only Cloud Agent runs server: laptop `http://127.0.0.1:8000` → expect refuse (documents the trap)  
4. After Tailscale/local Mac run: laptop or phone PWA reaches served URL, not raw public IP  

---

## 6. Acceptance criteria for the fix

- [ ] README warns that Cloud Agent `127.0.0.1` ≠ laptop `127.0.0.1`
- [ ] `make os-dev` prints full URL with `:8000` and topology note
- [ ] `DEV_HOST` / `DEV_PORT` overridable
- [ ] `make os-health` exists and passes when server is up on that host
- [ ] This bug spec + `tasks.md` + post-mortem committed

---

## 7. Related docs

- `docs/TAILSCALE.md` — remote access without exposing SQLite/Ollama
- `docs/PRODUCT_SPEC.md` — local-first deployment on M2 home host
- `Makefile` — `os-dev` target
