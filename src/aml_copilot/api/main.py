"""FastAPI application factory for the AML Investigation Copilot API."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aml_copilot.api.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="AML Investigation Copilot API",
        description=(
            "AI-powered Anti-Money Laundering (AML) Investigation Copilot API. "
            "Ingests bank statement PDFs, performs multi-agent evidence gathering, "
            "self-critique, and generates traceable compliance investigation reports."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Enable CORS for local Next.js frontend, Vercel deployments, and external clients
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routes at root and with /api prefix for maximum client compatibility
    app.include_router(router)
    app.include_router(router, prefix="/api")
    return app


app = create_app()
