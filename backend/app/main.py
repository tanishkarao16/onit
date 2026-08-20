from fastapi import FastAPI

from app.api.cases import router as cases_router


app = FastAPI(
    title="ONIT API",
    description="AI agent for resolving problems users don't have time to chase.",
    version="0.1.0",
)

app.include_router(cases_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "onit-api",
    }
