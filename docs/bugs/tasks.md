# Tasks — BUG-LOCALHOST-01 (browser cannot reach Aegis)

Tracked against: `docs/bugs/BUG-LOCALHOST-01.md`  
Post-mortem: `docs/postmortems/2026-09-07-localhost-connection-refused.md`

## Priority order

### P0 — Unblock developers (docs + Makefile clarity)

- [x] Diagnose: confirm uvicorn healthy on agent loopback; curl `/health` + `/` → 200
- [x] Write bug spec with RC-A (topology), RC-B (port), RC-C (bind)
- [x] Update `README.md` Quickstart with Cloud-Agent vs same-machine browser warning
- [x] Change `Makefile` `os-dev` to print full `http://127.0.0.1:8000/` URL + topology note
- [x] Add `DEV_HOST` / `DEV_PORT` make variables (default `127.0.0.1:8000`)
- [x] Add `make os-health` curl check for same-host verification
- [x] Update `AGENT_HANDOFF.md` with “how to open the UI” note

### P1 — Safer remote access path (no OAuth / no public expose)

- [ ] Document recommended path: run on Apple Silicon M2 host for local Chrome demos
- [ ] Cross-link `docs/TAILSCALE.md` for phone/PWA remote (auth-aware proxy only)
- [ ] If Cursor port preview/forward exists for the agent, document the exact URL pattern (env-specific)

### P2 — Hardening (optional)

- [ ] Consider defaulting cloud/devcontainer `DEV_HOST=0.0.0.0` only when an auth proxy is present
- [ ] Add a tiny integration test that asserts `/health` and `/` return 200 via TestClient (already covered) and a script `scripts/check_dev_server.sh` for live process checks
- [ ] Add Playwright/E2E later against a same-host server (out of scope for this bug)

### Verification checklist

- [ ] `make os-dev` on server host
- [ ] `make os-health` → JSON `status: ok`
- [ ] Same-host browser or curl: `http://127.0.0.1:8000/` → HTML contains `aegis`
- [ ] Confirm bare `http://127.0.0.1/` still fails unless intentionally proxied (documents RC-B)

## Out of scope for this bug

- Implementing live Tailscale Funnel
- Changing product features / scores / connectors
- Exposing the Cloud Agent port publicly on the internet
