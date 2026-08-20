from fastapi import FastAPI

app = FastAPI(
    title="ONIT API",
    description="AI agent for resolving problems users don't have time to chase.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "onit-api",
    }
