"""FastAPI application factory for the AML Investigation Copilot API."""

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

    # Enable CORS for local Next.js frontend and external development clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
