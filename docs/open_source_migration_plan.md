# Open Source Migration Plan

## Overview
This document outlines the migration setup from cloud APIs to a fully local, open-source runtime.

## Hardware Targets
- **M2/16 GB Default Path**: The baseline system for our local migration. Ensure all models (e.g., Llama 3/Mistral via Ollama, local Whisper/Piper) comfortably fit in this memory limit.
- **M4 Stretch Path**: Support for larger models and faster inference on high-end hardware.

## Installation & Setup
Review `AUTH_AND_SETUP_BUCKET_LIST.md` for the current status of prerequisites. Placeholders exist for missing items.
Required local installs:
- Docker
- Ollama
- Playwright
- Jaeger
- Whisper
- Piper

## Operating Modes
- **Optional Cloud Fallbacks**: When local inference fails or hardware constraints prevent execution, fallback to original cloud services.
- **Legacy Sponsor Mode**: Maintain original hackathon implementations for sponsors (Anthropic, Redis, Deepgram, Arize, Sentry, Fetch AI, Band, Simular, Cognition, Browserbase).
