"""
Task Agent Module
=================

Responsible for extracting actionable preparation tasks from a user's
meeting request. Uses Gemini via Google ADK to analyze the request
and return a structured list of concrete tasks.

Workflow:
    1. Receives the user's meeting preparation request
    2. Analyzes the request using Gemini to identify preparation needs
    3. Returns a structured list of actionable tasks

The agent is defined as an ADK LlmAgent with a specialized tool function
that formats the extracted tasks as structured output.
"""

import json
import logging
import os

from google.adk.agents import LlmAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task extraction tool
# ---------------------------------------------------------------------------


def extract_preparation_tasks(meeting_description: str) -> dict:
    """
    Analyze a meeting description and return a structured list of
    preparation tasks.

    This tool is called by the Task Agent to format its analysis
    into a consistent JSON structure.

    Args:
        meeting_description: The user's meeting request text.

    Returns:
        Dictionary with a 'tasks' key containing a list of task strings.
    """
    # The LLM handles the actual extraction logic — this tool function
    # provides the structured output format that the agent returns.
    logger.info("extract_preparation_tasks called for: %s", meeting_description[:80])

    # Return a structured placeholder that the LLM will populate
    # through its instruction-driven analysis
    return {
        "status": "tasks_extracted",
        "meeting_description": meeting_description,
    }


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")

TASK_AGENT_INSTRUCTION = """You are a Task Extraction Agent specialized in meeting preparation.

Your role is to analyze meeting requests and extract specific, actionable preparation tasks.

When given a meeting description, you MUST:
1. Identify the type of meeting (demo, review, planning, standup, etc.)
2. Extract 3-7 concrete preparation tasks that someone should complete before the meeting
3. Order tasks by priority (most important first)
4. Make each task specific and actionable (start with a verb)

IMPORTANT: You MUST respond with ONLY a valid JSON object in this exact format:
{
    "tasks": ["Task 1 description", "Task 2 description", "Task 3 description"]
}

Examples of good tasks:
- "Review and update presentation slides with latest metrics"
- "Rehearse demo flow including backup scenarios"
- "Prepare answers for anticipated stakeholder questions"
- "Test all demo environments and verify connectivity"
- "Gather latest performance metrics and KPI data"

Do NOT include any text outside the JSON object. Only output the JSON."""

task_agent = LlmAgent(
    model=MODEL_ID,
    name="task_agent",
    description=(
        "Extracts actionable preparation tasks from meeting requests. "
        "Returns a structured list of specific, prioritized tasks."
    ),
    instruction=TASK_AGENT_INSTRUCTION,
    tools=[extract_preparation_tasks],
)
