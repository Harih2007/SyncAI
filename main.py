"""
GenAI Meeting Preparation Assistant — Main Entry Point
======================================================

A production-ready multi-agent AI backend for meeting preparation,
built with FastAPI and Google Agent Development Kit (ADK).

Architecture:
    ┌─────────────────────────────────────────────────┐
    │                  FastAPI Server                  │
    │                   (main.py)                     │
    ├─────────────────────────────────────────────────┤
    │               Manager Agent                     │
    │    ┌──────────┬──────────────┬──────────────┐   │
    │    │  Task    │  Calendar    │    Info       │   │
    │    │  Agent   │  Agent       │    Agent      │   │
    │    └──────────┴──────────────┴──────────────┘   │
    │         │            │              │           │
    │    Gemini via    Calendar       Firestore       │
    │    Vertex AI     Tool          Client           │
    └─────────────────────────────────────────────────┘

Deployment:
    Designed for Google Cloud Run. Start with:
        uvicorn main:app --host 0.0.0.0 --port 8080

Environment Variables:
    PROJECT_ID                   — Google Cloud project ID
    GOOGLE_APPLICATION_CREDENTIALS — Path to service account key (local only)
    VERTEX_MODEL                 — Gemini model ID (default: gemini-2.0-flash)
"""

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GenAI Meeting Preparation Assistant",
    description=(
        "Multi-agent AI system for automated meeting preparation. "
        "Uses Google ADK with Gemini to extract tasks, schedule preparation "
        "time, and retrieve relevant notes from Firestore."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS middleware (allow Cloud Run and local development)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register API routes
# ---------------------------------------------------------------------------

app.include_router(router)

# ---------------------------------------------------------------------------
# Startup event
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    """
    Runs on application startup.

    Validates required environment variables and optionally seeds
    sample data into Firestore for demonstration purposes.
    """
    logger.info("=" * 60)
    logger.info("GenAI Meeting Preparation Assistant — Starting up")
    logger.info("=" * 60)

    # Log environment configuration (without secrets)
    project_id = os.environ.get("PROJECT_ID", "NOT SET")
    model_id = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "ADC (default)")

    logger.info("PROJECT_ID:    %s", project_id)
    logger.info("VERTEX_MODEL:  %s", model_id)
    logger.info("CREDENTIALS:   %s", creds_path)

    # Attempt to seed sample notes (non-blocking, non-fatal)
    try:
        from database.firestore_client import seed_sample_notes
        seed_sample_notes()
        logger.info("Firestore sample data check complete.")
    except Exception as exc:
        logger.warning(
            "Could not seed Firestore sample data (non-fatal): %s", exc
        )

    logger.info("Application ready to receive requests on port 8080.")


@app.on_event("shutdown")
async def shutdown_event():
    """Runs on application shutdown. Logs a clean shutdown message."""
    logger.info("GenAI Meeting Preparation Assistant — Shutting down.")


# ---------------------------------------------------------------------------
# Development server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Auto-reload in development
        log_level="info",
    )
