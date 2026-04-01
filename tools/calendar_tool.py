"""
Calendar Tool Module
====================

Provides tool functions that the Calendar Agent can invoke to create
suggested preparation time blocks for meeting tasks.

These are pure Python functions that Google ADK agents can call as tools.
They do NOT require external calendar APIs — they generate intelligent
time-block suggestions based on task characteristics.

Design Decision:
    Cloud Run containers are stateless and short-lived, so we avoid
    long-running connections or external calendar service dependencies.
    Instead, we compute schedule suggestions deterministically.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default schedule configuration
# ---------------------------------------------------------------------------

# Working hours window (24h format)
WORK_START_HOUR = 9
WORK_END_HOUR = 18

# Default task durations by keyword heuristic (minutes)
DURATION_MAP = {
    "review": 60,
    "rehearse": 45,
    "prepare": 60,
    "write": 45,
    "update": 30,
    "test": 60,
    "check": 20,
    "read": 30,
    "compile": 20,
    "send": 15,
    "create": 45,
    "draft": 40,
    "research": 60,
    "practice": 45,
    "finalize": 30,
    "organize": 30,
    "gather": 30,
    "setup": 30,
}

# Default duration if no keyword matches
DEFAULT_DURATION_MINUTES = 30


def estimate_task_duration(task_description: str) -> int:
    """
    Estimate the duration (in minutes) for a preparation task based on
    keyword matching against the task description.

    Args:
        task_description: Natural language description of the task.

    Returns:
        Estimated duration in minutes.
    """
    description_lower = task_description.lower()
    for keyword, duration in DURATION_MAP.items():
        if keyword in description_lower:
            return duration
    return DEFAULT_DURATION_MINUTES


def create_schedule_blocks(tasks: list[str], meeting_date: str = "") -> list[dict]:
    """
    Generate preparation time blocks for a list of tasks.

    Schedules tasks sequentially within working hours on the day before
    the meeting (or today if no meeting date is provided), with 15-minute
    buffer gaps between blocks.

    Args:
        tasks: List of task description strings to schedule.
        meeting_date: Optional ISO date string for the meeting day.
                      Defaults to tomorrow if not provided.

    Returns:
        List of schedule block dictionaries, each containing:
        - task: The task description
        - time: Human-readable time range string (e.g., "9:00 AM - 10:00 AM")
        - duration_minutes: Duration in minutes
        - priority: Priority level ("high", "medium", or "low")
    """
    if not tasks:
        return []

    # Determine the preparation date (day before meeting, or today)
    now = datetime.now(timezone.utc)
    if meeting_date:
        try:
            meeting_dt = datetime.fromisoformat(meeting_date).replace(
                tzinfo=timezone.utc
            )
            prep_date = meeting_dt - timedelta(days=1)
        except ValueError:
            # If parsing fails, default to today
            prep_date = now
    else:
        prep_date = now

    # Start scheduling from the beginning of working hours
    current_time = prep_date.replace(
        hour=WORK_START_HOUR, minute=0, second=0, microsecond=0
    )
    end_of_day = prep_date.replace(
        hour=WORK_END_HOUR, minute=0, second=0, microsecond=0
    )

    schedule: list[dict] = []
    buffer_minutes = 15  # Gap between tasks

    for i, task in enumerate(tasks):
        duration = estimate_task_duration(task)

        # Check if task fits within working hours
        task_end = current_time + timedelta(minutes=duration)
        if task_end > end_of_day:
            # Wrap to next available morning slot if overflows
            current_time = current_time.replace(
                hour=WORK_START_HOUR, minute=0
            ) + timedelta(days=1)
            task_end = current_time + timedelta(minutes=duration)

        # Assign priority based on task position (first tasks = higher priority)
        if i < len(tasks) // 3 or i == 0:
            priority = "high"
        elif i < 2 * len(tasks) // 3:
            priority = "medium"
        else:
            priority = "low"

        schedule.append(
            {
                "task": task,
                "time": (
                    f"{current_time.strftime('%I:%M %p')} - "
                    f"{task_end.strftime('%I:%M %p')}"
                ),
                "duration_minutes": duration,
                "priority": priority,
            }
        )

        # Advance current_time past this block + buffer
        current_time = task_end + timedelta(minutes=buffer_minutes)

    logger.info("Created %d schedule blocks for %d tasks", len(schedule), len(tasks))
    return schedule
