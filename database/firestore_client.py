"""
Firestore Client Module
=======================

Provides a centralized Firestore client and helper functions for the
Meeting Preparation Assistant. All Firestore interactions are routed
through this module to ensure consistent connection management and
error handling.

Collections:
    - meeting_tasks: Stores extracted preparation tasks
    - meeting_notes: Stores notes and information related to meeting topics
    - meeting_results: Stores complete meeting preparation results

Environment Variables:
    - PROJECT_ID: Google Cloud project ID (required)
    - GOOGLE_APPLICATION_CREDENTIALS: Path to service account key (optional on Cloud Run)
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firestore client singleton
# ---------------------------------------------------------------------------

_firestore_client: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """
    Returns a singleton Firestore client instance.

    On Google Cloud Run, Application Default Credentials (ADC) are
    automatically available via the metadata server. Locally, set
    GOOGLE_APPLICATION_CREDENTIALS to a service account key JSON path.
    """
    global _firestore_client
    if _firestore_client is None:
        project_id = os.environ.get("PROJECT_ID")
        if not project_id:
            logger.warning(
                "PROJECT_ID not set — Firestore client will use ADC project."
            )
        _firestore_client = firestore.Client(project=project_id)
        logger.info("Firestore client initialized for project: %s", project_id)
    return _firestore_client


# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------


def store_tasks(session_id: str, tasks: list[str]) -> str:
    """
    Persist a list of preparation tasks in Firestore.

    Args:
        session_id: Unique identifier for the preparation session.
        tasks: List of task description strings.

    Returns:
        The Firestore document ID of the stored record.
    """
    db = get_firestore_client()
    doc_ref = db.collection("meeting_tasks").document(session_id)
    doc_ref.set(
        {
            "tasks": tasks,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
        }
    )
    logger.info("Stored %d tasks for session %s", len(tasks), session_id)
    return doc_ref.id


# ---------------------------------------------------------------------------
# Notes / information helpers
# ---------------------------------------------------------------------------


def retrieve_notes(topic: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Query Firestore for notes matching the given topic keyword.

    Performs a case-insensitive keyword search across the ``tags`` array
    field of documents in the ``meeting_notes`` collection.

    Args:
        topic: Keyword to search for in note tags.
        limit: Maximum number of notes to return (default 5).

    Returns:
        List of note dictionaries containing ``title``, ``content``, and ``tags``.
    """
    db = get_firestore_client()
    notes: list[dict[str, Any]] = []

    try:
        # Try to find notes where the topic appears in the tags array
        query = (
            db.collection("meeting_notes")
            .where("tags", "array_contains", topic.lower())
            .limit(limit)
        )
        docs = query.stream()

        for doc in docs:
            data = doc.to_dict()
            notes.append(
                {
                    "id": doc.id,
                    "title": data.get("title", "Untitled"),
                    "content": data.get("content", ""),
                    "tags": data.get("tags", []),
                }
            )

        # Fallback: if no tagged notes found, return the most recent notes
        if not notes:
            fallback_query = (
                db.collection("meeting_notes")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            for doc in fallback_query.stream():
                data = doc.to_dict()
                notes.append(
                    {
                        "id": doc.id,
                        "title": data.get("title", "Untitled"),
                        "content": data.get("content", ""),
                        "tags": data.get("tags", []),
                    }
                )

    except Exception as exc:
        logger.warning("Firestore notes query failed: %s", exc)
        # Return empty list gracefully — the Info Agent will handle it
        notes = []

    logger.info("Retrieved %d notes for topic '%s'", len(notes), topic)
    return notes


# ---------------------------------------------------------------------------
# Meeting result helpers
# ---------------------------------------------------------------------------


def save_meeting_result(session_id: str, result: dict[str, Any]) -> str:
    """
    Save a complete meeting preparation result to Firestore.

    Args:
        session_id: Unique session identifier.
        result: Dictionary containing tasks, schedule, and notes_summary.

    Returns:
        The Firestore document ID of the stored result.
    """
    db = get_firestore_client()
    doc_ref = db.collection("meeting_results").document(session_id)
    doc_ref.set(
        {
            **result,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
        }
    )
    logger.info("Saved meeting result for session %s", session_id)
    return doc_ref.id


def seed_sample_notes() -> None:
    """
    Seeds sample notes into Firestore for demonstration purposes.

    This function is idempotent — it checks whether sample data already
    exists before writing.
    """
    db = get_firestore_client()
    collection = db.collection("meeting_notes")

    # Check if sample data already exists
    existing = collection.where("is_sample", "==", True).limit(1).stream()
    if any(True for _ in existing):
        logger.info("Sample notes already exist — skipping seed.")
        return

    sample_notes = [
        {
            "title": "Project Demo Metrics",
            "content": (
                "Key product metrics: DAU increased 15% MoM. "
                "API latency reduced to 120ms p99. "
                "Customer satisfaction score at 4.6/5. "
                "Three new enterprise clients onboarded this quarter."
            ),
            "tags": ["project", "demo", "metrics", "product"],
            "is_sample": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "title": "Sprint Retrospective Notes",
            "content": (
                "Team velocity improved by 20%. "
                "Key blocker: CI/CD pipeline instability resolved. "
                "Action items: improve test coverage to 85%, "
                "adopt trunk-based development."
            ),
            "tags": ["sprint", "retrospective", "team", "meeting"],
            "is_sample": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "title": "Q4 Planning Overview",
            "content": (
                "Focus areas: Platform scalability, ML model deployment, "
                "and developer experience improvements. "
                "Budget approved for two new hires. "
                "Key milestone: public beta launch by end of Q4."
            ),
            "tags": ["planning", "quarterly", "roadmap", "project"],
            "is_sample": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    for note in sample_notes:
        collection.add(note)

    logger.info("Seeded %d sample notes into Firestore.", len(sample_notes))
