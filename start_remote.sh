#!/bin/bash
# Remote Access Script for Aegis (Task 14)

echo "Starting Aegis remote access via Tailscale Funnel..."
echo "Ensure Tailscale is installed and Funnel is enabled on your account."
echo ""
echo "Exposing local port 8000..."

# Start the funnel targeting the FastAPI port
tailscale funnel 8000
