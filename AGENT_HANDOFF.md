# Agent Handoff

## Migration Setup

The migration to the open-source runtime environment focuses on local first execution.

- **M2/16 GB Default Path**: The default target hardware. Ensure local models and services fit within this memory envelope.
- **M4 Stretch Path**: Extended capabilities for newer M4 hardware. 
- **Required Local Installs**:
  - Python 3.10+
  - Local model runners (e.g., Ollama)
  - Testing tools (Playwright)
- **Optional Cloud Fallbacks**: If local execution struggles, cloud APIs (Anthropic, Deepgram) remain available as fallbacks.
- **Legacy Sponsor Mode**: Maintained for sponsor tracks (Anthropic, Redis, Deepgram, Arize, Sentry, Fetch AI, Band, Simular, Cognition, Browserbase).
