"""
Calendar Agent Module
=====================

Responsible for creating suggested preparation time blocks for
identified tasks. Uses the calendar_tool to generate intelligent
schedule suggestions within working hours.

Workflow:
    1. Receives a list of preparation tasks (from the Task Agent)
    2. Uses the schedule_preparation_blocks tool to create time blocks
    3. Returns a structured schedule with time ranges and priorities

The agent is defined as an ADK LlmAgent with access to the scheduling
tool function.
"""

import json
import logging
import os

from google.adk.agents import LlmAgent

from tools.calendar_tool import create_schedule_blocks, estimate_task_duration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scheduling tool (exposed to the agent)
# ---------------------------------------------------------------------------


def schedule_preparation_blocks(tasks_json: str, meeting_date: str = "") -> dict:
    """
    Create preparation time blocks for a list of tasks.

    Parses the tasks from a JSON string and delegates to the calendar
    tool to generate schedule blocks within working hours.

    Args:
        tasks_json: JSON string containing a list of task descriptions.
                    Example: '["Review slides", "Rehearse demo"]'
        meeting_date: Optional ISO date string for the meeting.

    Returns:
        Dictionary with a 'schedule' key containing time block details.
    """
    logger.info("schedule_preparation_blocks called")

    try:
        tasks = json.loads(tasks_json) if isinstance(tasks_json, str) else tasks_json
    except (json.JSONDecodeError, TypeError):
        # If parsing fails, treat the input as a single task
        tasks = [str(tasks_json)]

    schedule = create_schedule_blocks(tasks, meeting_date)

    return {
        "status": "schedule_created",
        "schedule": schedule,
        "total_blocks": len(schedule),
        "total_minutes": sum(
            estimate_task_duration(t) for t in tasks
        ),
    }


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")

CALENDAR_AGENT_INSTRUCTION = """You are a Calendar Scheduling Agent specialized in meeting preparation planning.

Your role is to take a list of preparation tasks and create an optimized schedule with time blocks.

When given tasks, you MUST:
1. Use the schedule_preparation_blocks tool to generate time blocks
2. Pass the tasks as a JSON array string to the tool
3. Return the schedule in the exact JSON format specified below

IMPORTANT: You MUST respond with ONLY a valid JSON object in this exact format:
{
    "schedule": [
        {"task": "Task description", "time": "9:00 AM - 10:00 AM"},
        {"task": "Another task", "time": "10:15 AM - 11:00 AM"}
    ]
}

Guidelines:
- Schedule high-priority tasks earlier in the day
- Include buffer time between blocks (15 minutes)
- Keep blocks within working hours (9 AM - 6 PM)
- Estimate realistic durations based on task complexity

Do NOT include any text outside the JSON object. Only output the JSON."""

calendar_agent = LlmAgent(
    model=MODEL_ID,
    name="calendar_agent",
    description=(
        "Creates optimized preparation schedules with time blocks. "
        "Takes a list of tasks and returns a structured schedule."
    ),
    instruction=CALENDAR_AGENT_INSTRUCTION,
    tools=[schedule_preparation_blocks],
)
