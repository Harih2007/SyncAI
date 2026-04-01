"""
Manager Agent Module
====================

The central orchestrator for the Meeting Preparation Assistant.
Coordinates the Task Agent, Calendar Agent, and Info Agent to produce
a complete meeting preparation plan.

Architecture:
    The Manager Agent is implemented as a programmatic orchestrator
    (not an LLM-based router) to ensure deterministic, reliable execution
    order. This is critical for production Cloud Run deployments where
    predictability and latency consistency matter.

Workflow:
    1. Accepts the user's meeting preparation request
    2. Invokes Task Agent → extracts preparation tasks
    3. Invokes Calendar Agent → creates schedule blocks for those tasks
    4. Invokes Info Agent → retrieves relevant notes from Firestore
    5. Merges all outputs into a unified meeting preparation plan
    6. Persists the result in Firestore
    7. Returns the structured JSON response
"""

import json
import logging
import os
import uuid
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from database.firestore_client import save_meeting_result, store_tasks

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")

# ---------------------------------------------------------------------------
# Import sub-agents
# ---------------------------------------------------------------------------

from agents.task_agent import task_agent
from agents.calendar_agent import calendar_agent
from agents.info_agent import info_agent


# ---------------------------------------------------------------------------
# Helper: Run a single agent and extract its text response
# ---------------------------------------------------------------------------


async def _run_agent(
    agent: LlmAgent,
    user_message: str,
    app_name: str = "meeting_assistant",
) -> str:
    """
    Execute a single ADK agent and return its final text response.

    Creates a fresh InMemoryRunner and session for each invocation to
    ensure stateless execution (required for Cloud Run).

    Args:
        agent: The ADK LlmAgent to execute.
        user_message: The input message to send to the agent.
        app_name: Application name for session management.

    Returns:
        The agent's final text response as a string.
    """
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    session = await runner.session_service.create_session(
        app_name=app_name,
        user_id=user_id,
    )

    final_response = ""

    # Create the user message content
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_content,
    ):
        # Collect the final agent response from events
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_response = part.text  # Keep the last text response

    return final_response


# ---------------------------------------------------------------------------
# Helper: Parse JSON from agent response
# ---------------------------------------------------------------------------


def _parse_agent_json(response: str, fallback_key: str) -> dict[str, Any]:
    """
    Parse a JSON object from an agent's text response.

    Handles cases where the agent wraps JSON in markdown code fences
    or includes extra text before/after the JSON.

    Args:
        response: Raw text response from the agent.
        fallback_key: Key name to use if parsing fails.

    Returns:
        Parsed dictionary, or a fallback dict if parsing fails.
    """
    # Strip markdown code fences if present
    cleaned = response.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = cleaned.index("\n") if "\n" in cleaned else 3
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        # Try to find a JSON object in the response
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        json_str = cleaned[start:end]
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "Failed to parse JSON from agent response: %s — Error: %s",
            response[:200],
            exc,
        )
        return {fallback_key: response}


# ---------------------------------------------------------------------------
# Main orchestration function
# ---------------------------------------------------------------------------


async def run_meeting_preparation(user_message: str) -> dict[str, Any]:
    """
    Orchestrate the full meeting preparation workflow.

    This is the main entry point called by the API layer. It runs all
    three sub-agents sequentially and merges their outputs.

    Args:
        user_message: The user's meeting preparation request.

    Returns:
        Dictionary containing:
        - tasks: List of preparation task strings
        - schedule: List of schedule block dicts with task and time
        - notes_summary: Summary string of relevant notes

    Example:
        >>> result = await run_meeting_preparation(
        ...     "Prepare my project demo meeting tomorrow"
        ... )
        >>> result
        {
            "tasks": ["Review slides", "Rehearse demo"],
            "schedule": [
                {"task": "Review slides", "time": "9:00 AM - 10:00 AM"},
                {"task": "Rehearse demo", "time": "10:15 AM - 11:00 AM"}
            ],
            "notes_summary": "Key product metrics and latest updates."
        }
    """
    session_id = uuid.uuid4().hex
    logger.info("Starting meeting preparation — session: %s", session_id)

    # -----------------------------------------------------------------------
    # Step 1: Task Agent — Extract preparation tasks
    # -----------------------------------------------------------------------
    logger.info("[Step 1/3] Running Task Agent...")
    task_response = await _run_agent(
        task_agent,
        f"Extract preparation tasks for this meeting request: {user_message}",
    )
    task_data = _parse_agent_json(task_response, "tasks")
    tasks = task_data.get("tasks", [])

    # Ensure tasks is a list of strings
    if not isinstance(tasks, list):
        tasks = [str(tasks)]
    tasks = [str(t) for t in tasks]

    logger.info("Task Agent returned %d tasks", len(tasks))

    # -----------------------------------------------------------------------
    # Step 2: Calendar Agent — Schedule preparation blocks
    # -----------------------------------------------------------------------
    logger.info("[Step 2/3] Running Calendar Agent...")
    tasks_json = json.dumps(tasks)
    calendar_response = await _run_agent(
        calendar_agent,
        f"Create a preparation schedule for these tasks: {tasks_json}",
    )
    calendar_data = _parse_agent_json(calendar_response, "schedule")
    schedule = calendar_data.get("schedule", [])

    # Ensure schedule entries have the required format
    cleaned_schedule = []
    for entry in schedule:
        if isinstance(entry, dict):
            cleaned_schedule.append(
                {
                    "task": entry.get("task", "Unknown task"),
                    "time": entry.get("time", "TBD"),
                }
            )
        else:
            cleaned_schedule.append({"task": str(entry), "time": "TBD"})

    logger.info("Calendar Agent returned %d schedule blocks", len(cleaned_schedule))

    # -----------------------------------------------------------------------
    # Step 3: Info Agent — Retrieve relevant notes
    # -----------------------------------------------------------------------
    logger.info("[Step 3/3] Running Info Agent...")
    info_response = await _run_agent(
        info_agent,
        f"Find relevant notes and information for this meeting: {user_message}",
    )
    info_data = _parse_agent_json(info_response, "notes_summary")
    notes_summary = info_data.get(
        "notes_summary",
        "No additional notes found for this meeting topic.",
    )

    logger.info("Info Agent returned notes summary")

    # -----------------------------------------------------------------------
    # Step 4: Merge outputs into final result
    # -----------------------------------------------------------------------
    result = {
        "tasks": tasks,
        "schedule": cleaned_schedule,
        "notes_summary": notes_summary,
    }

    # -----------------------------------------------------------------------
    # Step 5: Persist result to Firestore
    # -----------------------------------------------------------------------
    try:
        store_tasks(session_id, tasks)
        save_meeting_result(session_id, result)
        logger.info("Results persisted to Firestore — session: %s", session_id)
    except Exception as exc:
        # Non-fatal: log the error but still return the result
        logger.error("Failed to persist results to Firestore: %s", exc)

    logger.info("Meeting preparation complete — session: %s", session_id)
    return result
