from fastapi import FastAPI

app = FastAPI(title="OS Migration Foundation")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "mode": "open-source-foundation"}
