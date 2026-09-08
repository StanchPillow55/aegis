# Connector auth & sync policy (operator note 2026-09-08)

Authoritative product decisions for external health sync. Do **not** reintroduce Fitbit-as-primary or scale OAuth.

## Primary metric sync — Google Health

- **Google Health / Fit Takeout (and future Google Health API)** is the **primary** wearable/metric sync path.
- Prefer Takeout ZIP / Google Health import for historical + bulk metrics.
- Live Google Health API can be added when credentials exist; do not block Goal Graph on it.

## Calendar — Google OAuth (keep)

- **Google Calendar read-only OAuth remains the intended live calendar path.**
- Scaffold: `/api/google/calendar/{status,auth,callback,events,revoke}` — needs `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET`.
- Fixture calendar events cover offline/demo; live OAuth is still the real calendar connector.
- Do not replace Calendar with Fitbit calendar hacks.

## Google Health API — live scaffold (primary with Takeout)

- Live Fitness API OAuth scaffold: `/api/google/health/{status,auth,callback,pull,revoke}`.
- Without secrets → `needs_credentials` (never fake authenticated).
- With secrets but no token → `configured` + `auth_url`.
- Bulk/historical import remains Takeout ZIP (preview→confirm).

## FITINDEX / body scale — no scale OAuth

- Scale vendor OAuth has **never been used** and is **out of scope**.
- Stick with:
  - **CSV export** upload + user review before save
  - **Screenshot / image OCR** (local llava optional) → draft → user confirm
  - Manual metric entry
- Do not build or fake FITINDEX/scale OAuth.

## Fitbit — not primary (deprecated path)

- **Do not use Fitbit API as the primary sync metric.**
- Fitbit OAuth refresh cadence is too aggressive for this product’s local-first loop.
- Keep fixture / legacy scaffold only for compatibility tests (`PHC-FITBIT-01` fixture-verified).
- UI should label Fitbit as **legacy fixture / not primary**, not as the main connect button.

## Honesty rules

- Never fake OAuth success.
- Never claim live Fitbit pull when using fixtures.
- Token storage security checklist still applies to **Google** OAuth (Calendar / future Health), not to inventing Fitbit live.
