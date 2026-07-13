# Legacy Hackathon Implementation

This folder contains the original sponsor-integrated implementation of `aegis` built during Cal Hacks 2026.

## Why was this archived?
The original implementation was heavily reliant on paid cloud APIs, sponsor tracks, and privileged services. As part of our open-source migration (`[OS-MIGRATION]`), we converted the project into a local-first, openly-downloadable runtime that can run on an M2 / 16GB Apple Silicon MacBook without external dependencies. 

## Which sponsor integrations were used here?
- **Anthropic**: Used for data extraction from unstructured transcripts and directive synthesis.
- **Deepgram**: Used for primary voice input/output (STT/TTS).
- **Redis (Redis Cloud)**: Used for vector search, memory, and context retrieval.
- **Sentry**: Used for observability, tracing agent hops and external calls.
- **Fetch AI / uAgents**: Used as the orchestrator and agent framework.
- **Arize / Phoenix**: Used for AI evaluations (directive grounding score).
- **Browserbase & Stagehand**: Used for WOD importing and UI E2E tests.
- **Band**: Used for agent-to-agent message bus.
- **Simular / Sai**: Used for demo loop automation.
- **Cognition (Devin)**: Used to build non-trivial modules in the codebase.

## How to restore or reference it
You can view the original PRs and `success_criteria.yaml` history in the commit logs prior to the `feat/open-source-runtime-migration` branch. The file structure here remains exactly as it was during the hackathon submission.
