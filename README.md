# aegis

**Daily training-decision copilot for functional longevity** — expanding into a **local-first personal health copilot**.

Still centered on one evidence-bound daily training directive:

`Intake → structured health data → evidence → scores → WOD/training context → directive`

## Docs (read in order)
1. [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — canonical product + architecture spec  
2. [`success_criteria.yaml`](success_criteria.yaml) — Definition of Done (automation)  
3. [`docs/SC_MATURITY.md`](docs/SC_MATURITY.md) — verified vs fixture vs planned  
4. [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) — current state + next slice  
5. [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) — next-agent implementation plan  
6. [`docs/FEATURE_MERGE_MATRIX.md`](docs/FEATURE_MERGE_MATRIX.md) — cross-prototype feature status  
7. [`CLAUDE.md`](CLAUDE.md) — build contract  

## Quickstart (Apple Silicon M2 or Linux)
```bash
cp .env.example .env
python3 -m pip install -r requirements.txt
make os-test
make os-demo
make os-dev   # alias: make dev — http://127.0.0.1:8000/
make os-health  # same-host proof the server is up
```

Then open **`http://127.0.0.1:8000/`** in a browser **on the same machine** that is running `make os-dev`.

### Browser cannot connect? (`ERR_CONNECTION_REFUSED`)

`127.0.0.1` means **this computer only**.

| Where `make os-dev` runs | Where Chrome runs | Result |
|---|---|---|
| Your M2 Mac | Same Mac | Works at `http://127.0.0.1:8000/` |
| Cursor Cloud Agent / remote VM | Your laptop | **Fails** — laptop localhost ≠ agent localhost |

Also include the port: `http://127.0.0.1:8000/` — bare `http://127.0.0.1/` hits port 80 and will refuse.

See bug spec: [`docs/bugs/BUG-LOCALHOST-01.md`](docs/bugs/BUG-LOCALHOST-01.md).  
Remote phone/PWA access: [`docs/TAILSCALE.md`](docs/TAILSCALE.md).

Optional: `ollama pull llama3.2`  
Override bind for tunnels (behind auth): `make os-dev DEV_HOST=0.0.0.0`

## Local-first boundary
LLM, storage, scoring, and reasoning are local. External connectors are optional and fail soft. No cloud LLM/DB required.

## Build philosophy
Agentic loop governed by `success_criteria.yaml`. See `CLAUDE.md`.
