# Post-mortem — Localhost `ERR_CONNECTION_REFUSED` while Aegis “is running”

**Date:** 2026-09-07  
**Incident window:** User ran `make os-dev` in the Cloud Agent terminal, then opened Chrome to `127.0.0.1` and received `ERR_CONNECTION_REFUSED`.  
**Severity:** High for demo/UI workflow; low for backend correctness (API was healthy).  
**Status:** Root-caused; fixes documented and partially implemented in-repo.  
**Bug spec:** `docs/bugs/BUG-LOCALHOST-01.md`  
**Tasks:** `docs/bugs/tasks.md`

---

## Summary

The Aegis server process was **up and healthy** on the Cloud Agent VM (`127.0.0.1:8000`, `/health` → `ok`, `/` → `200`). The user’s browser failed because **`127.0.0.1` referred to a different machine** (the laptop), and possibly because the URL omitted **`:8000`** (port 80 has no listener). This was an environment/topology footgun, not an application crash.

---

## Timeline

1. Autonomously implemented product slices; `make os-dev` documented as `http://127.0.0.1:8000`.
2. User started `make os-dev` in the agent terminal; uvicorn logged “Running on http://127.0.0.1:8000”.
3. User opened Chrome (local machine) to `127.0.0.1` → refused.
4. Investigation on the agent host: port 8000 LISTEN; curl health/UI succeed; port 80 refuses.
5. Spec + tasks + this post-mortem written; Makefile/README fixes applied.

---

## Impact

- Blocked visual confirmation of the UI after successful terminal start.
- Created false impression that the app “doesn’t work” despite green API health.
- Wasted time chasing FastAPI/CORS/frontend bugs that were not involved.

---

## Root causes

1. **Primary — Loopback ambiguity across hosts:** Cloud Agent shell ≠ laptop browser; both say `127.0.0.1` but are not the same network namespace.
2. **Secondary — Port ambiguity:** Bare `http://127.0.0.1/` hits :80; app listens on :8000 only. Screenshot phrasing is consistent with a missing port.
3. **Contributing — Docs assumed same-machine demos** (M2 host) without a hard warning for Cloud Agent users.

---

## What went well

- Server actually started cleanly; logs were accurate.
- Same-host curl quickly proved the app was fine (narrowed to topology in minutes).
- Binding to `127.0.0.1` by default remains a good security default for local-only mode.

---

## What went poorly

- Quickstart did not scream “Cloud Agent 127.0.0.1 ≠ your laptop.”
- `os-dev` did not print a topology warning next to the listen URL.
- No `os-health` helper for “prove the server on THIS host.”

---

## Corrective actions

| Action | Owner | Done? |
|---|---|---|
| Bug spec with RC-A/B/C + detailed fixes | Agent | Yes — `docs/bugs/BUG-LOCALHOST-01.md` |
| Task list | Agent | Yes — `docs/bugs/tasks.md` |
| Makefile: `DEV_HOST`/`DEV_PORT`, louder URL banner, `os-health` | Agent | In this change set |
| README topology warning | Agent | In this change set |
| Handoff “how to open UI” note | Agent | In this change set |
| Live OAuth / public port expose | — | Explicitly out of scope |

---

## Lessons learned

1. **Always qualify “localhost” with which host** when using remote agents.
2. **Always include the port** in printed URLs (`:8000`).
3. **Verify with curl on the server host before debugging the framework.**
4. Local-first products still need **remote-dev ergonomics** (warnings, health targets, Tailscale docs).

---

## Follow-up detection

If a user reports “running but browser refused”:

1. Run `make os-health` in the same environment as `os-dev`.
2. If health passes → ask whether the browser is on the same machine as the shell.
3. If they used `http://127.0.0.1/` without `:8000` → RC-B.
4. If Cloud Agent + laptop browser → RC-A; direct them to same-host M2 run or Tailscale path.
