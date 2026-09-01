from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cases import router as cases_router


app = FastAPI(
    title="ONIT API",
    description="AI agent for resolving problems users don't have time to chase.",
    version="0.1.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
# Allows the ONIT frontend deployed on Vercel to communicate
# with the FastAPI backend deployed on Render.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://onit-murex.vercel.app",
        "https://onit-git-main-tanishkarao16s-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------
app.include_router(cases_router)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "onit-api",
    }