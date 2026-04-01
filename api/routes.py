"""
API Routes Module
=================

Defines the FastAPI router with all HTTP endpoints for the Meeting
Preparation Assistant.

Endpoints:
    POST /chat         — Submit a meeting preparation request
    GET  /health       — Health check for Cloud Run / load balancers
    GET  /             — Root endpoint with API documentation links

Request/Response Models:
    - ChatRequest:  Pydantic model for incoming chat messages
    - ChatResponse: Pydantic model for meeting preparation results
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.manager_agent import run_meeting_preparation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router instance
# ---------------------------------------------------------------------------

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Request model for the /chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The meeting preparation request message.",
        json_schema_extra={
            "examples": ["Prepare my project demo meeting tomorrow"]
        },
    )


class ScheduleBlock(BaseModel):
    """A single time block in the preparation schedule."""

    task: str = Field(..., description="Description of the preparation task.")
    time: str = Field(..., description="Suggested time range (e.g., '3PM-4PM').")


class ChatResponse(BaseModel):
    """Response model for the /chat endpoint."""

    tasks: list[str] = Field(
        ..., description="List of extracted preparation tasks."
    )
    schedule: list[ScheduleBlock] = Field(
        ..., description="Suggested preparation time blocks."
    )
    notes_summary: str = Field(
        ..., description="Summary of relevant notes and information."
    )
    processing_time_seconds: Optional[float] = Field(
        None, description="Server-side processing time in seconds."
    )


class HealthResponse(BaseModel):
    """Response model for the /health endpoint."""

    status: str = "healthy"
    service: str = "meeting-preparation-assistant"
    version: str = "1.0.0"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    summary="API Root",
    description="Returns service information and available endpoints.",
    tags=["General"],
)
async def root():
    """Root endpoint providing API overview and documentation links."""
    return {
        "service": "GenAI Meeting Preparation Assistant",
        "version": "1.0.0",
        "description": (
            "Multi-agent AI system for automated meeting preparation. "
            "Submit a meeting request to /chat to get tasks, schedule, "
            "and relevant notes."
        ),
        "endpoints": {
            "POST /chat": "Submit a meeting preparation request",
            "GET /health": "Service health check",
            "GET /docs": "Interactive API documentation (Swagger UI)",
            "GET /redoc": "Alternative API documentation (ReDoc)",
        },
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns service health status for Cloud Run and load balancers.",
    tags=["General"],
)
async def health_check():
    """
    Health check endpoint.

    Cloud Run uses this to determine if the container is ready to
    receive traffic. Returns a simple JSON status response.
    """
    return HealthResponse()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Meeting Preparation",
    description=(
        "Submit a meeting preparation request. The system will use "
        "multiple AI agents to extract tasks, create a schedule, and "
        "retrieve relevant notes."
    ),
    tags=["Meeting Preparation"],
    responses={
        200: {
            "description": "Successful meeting preparation plan",
            "content": {
                "application/json": {
                    "example": {
                        "tasks": ["Review slides", "Rehearse demo"],
                        "schedule": [
                            {"task": "Review slides", "time": "3PM-4PM"},
                            {"task": "Rehearse demo", "time": "6PM-7PM"},
                        ],
                        "notes_summary": (
                            "Key product metrics and latest updates."
                        ),
                        "processing_time_seconds": 4.2,
                    }
                }
            },
        },
        422: {"description": "Validation error — invalid request body"},
        500: {"description": "Internal server error during agent execution"},
    },
)
async def chat(request: ChatRequest):
    """
    Process a meeting preparation request through the multi-agent system.

    Workflow:
        1. Manager Agent receives the request
        2. Task Agent extracts preparation tasks
        3. Calendar Agent schedules preparation time blocks
        4. Info Agent retrieves relevant notes from Firestore
        5. All outputs are merged into a structured response

    Args:
        request: ChatRequest containing the user's message.

    Returns:
        ChatResponse with tasks, schedule, and notes_summary.

    Raises:
        HTTPException: If agent execution fails.
    """
    start_time = time.time()
    logger.info("Received chat request: %s", request.message[:100])

    try:
        result = await run_meeting_preparation(request.message)

        processing_time = round(time.time() - start_time, 2)
        logger.info("Request processed in %.2f seconds", processing_time)

        return ChatResponse(
            tasks=result.get("tasks", []),
            schedule=[
                ScheduleBlock(**block) for block in result.get("schedule", [])
            ],
            notes_summary=result.get(
                "notes_summary",
                "No additional notes found.",
            ),
            processing_time_seconds=processing_time,
        )

    except Exception as exc:
        processing_time = round(time.time() - start_time, 2)
        logger.error(
            "Agent execution failed after %.2fs: %s",
            processing_time,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Meeting preparation failed",
                "message": str(exc),
                "processing_time_seconds": processing_time,
            },
        )
