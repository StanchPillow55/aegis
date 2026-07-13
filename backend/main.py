from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.providers.tracing import init_tracing
from backend.providers.llm import extract_intake
from backend.agents.orchestrator import orchestrator

# Initialize OpenTelemetry tracing
init_tracing()

app = FastAPI(title="aegis open-source runtime")

class AudioTranscriptRequest(BaseModel):
    transcript: str

class DemoResponse(BaseModel):
    directive: str

@app.post("/demo", response_model=DemoResponse)
def run_demo(request: AudioTranscriptRequest):
    try:
        # Step 1: Extract intake from text
        intake = extract_intake(request.transcript)
        
        # Step 2: Orchestrate (Memory, Scoring, Directive generation)
        directive = orchestrator.process_intake(intake)
        
        return DemoResponse(directive=directive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
