# aegis

Voice-first fitness tracking copilot for functional longevity.

Talk about your day — how you slept, what hurts, what you ate, how the workout went — and aegis turns it into structured data, scores your readiness, stores everything for long-term pattern analysis, and gives you one actionable training directive.

## Architecture

```
iPad/Phone (Safari)  →  Next.js Dashboard  →  FastAPI Backend  →  Ollama (local LLM)
                                                    ↓
                                          SQLite + ChromaDB (on disk)
```

- **Input:** Apple dictation in browser (free, built-in) + screenshot upload for WODs
- **Extraction:** Ollama + Llama 3.2 8B (local, free) with optional Claude Haiku fallback
- **Scoring:** Deterministic rule-based scorers (sleep, soreness, diet, hydration, performance, readiness)
- **Storage:** SQLite (structured logs, time-series) + ChromaDB (semantic vector search)
- **Patterns:** SQL aggregates + vector similarity + LLM-generated insights
- **Frontend:** Next.js 14 mobile-first dashboard with calendar, trend charts, and daily entry

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai) installed and running

### Setup

```bash
# 1. Pull Ollama models
ollama pull llama3.2
ollama pull llava

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd src/frontend && npm install && cd ../..

# 4. Copy env and configure
cp .env.example .env

# 5. Run tests to verify
make test

# 6. Start backend (terminal 1)
make backend

# 7. Start frontend (terminal 2)
make frontend
```

### Remote Access (iPad/Phone)

**Option A: Tailscale** (recommended)
```bash
# Install Tailscale on Mac and iPad
# Both devices get private IPs on your Tailnet
# Access aegis at http://[mac-tailscale-ip]:3000
```

**Option B: Cloudflare Tunnel** (public URL, no port forwarding)
```bash
brew install cloudflare/cloudflare/cloudflared
cloudflared tunnel --url http://localhost:3000
```

## Usage

1. Open aegis on iPad/Mac browser
2. Tap "Log" → use dictation button to speak your update
3. Optionally upload a WOD screenshot from the CrossFit app
4. View scores, trends, and insights on the dashboard
5. Browse the calendar for historical patterns

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/intake` | Submit daily entry (text + optional image) |
| GET | `/api/logs` | List logs by date range |
| GET | `/api/logs/{date}` | Get single day's log |
| GET | `/api/trends/scores` | Score time-series for charts |
| GET | `/api/trends/weekly` | Weekly averages |
| GET | `/api/trends/direction` | Trend direction (up/down/flat) |
| GET | `/api/patterns/search` | Semantic search across history |
| GET | `/api/patterns/performance-predictors` | What precedes best days? |
| GET | `/api/patterns/insight` | LLM-generated weekly insight |
| GET | `/api/directive` | Today's training recommendation |
| GET | `/health` | Server health check |

## Cost

$0/month. Everything runs locally:
- Ollama = free, local inference
- SQLite + ChromaDB = files on disk
- Apple dictation = built into Safari
- Tailscale free tier = remote access

Optional: Add `ANTHROPIC_API_KEY` for Claude Haiku extraction (~$0.001/entry).

## Data

All data lives in `./data/` (gitignored):
- `aegis.db` — SQLite database
- `chroma/` — ChromaDB vector store

Back up this directory to preserve history.

## Project Structure

```
src/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── models/intake.py     # All Pydantic models
│   ├── extraction/          # Ollama + Claude + Vision extraction
│   ├── scorers/             # Sleep, soreness, diet, hydration, performance, readiness
│   ├── storage/             # SQLite + ChromaDB
│   ├── patterns/            # Trends, correlations, insights
│   ├── api/                 # FastAPI route modules
│   └── importers/           # Fitbit + Google Health importers
└── frontend/
    ├── app/                 # Next.js App Router pages
    ├── components/          # React components
    └── lib/                 # API client helpers
```

Legacy hackathon code is preserved in `./legacy/`.
