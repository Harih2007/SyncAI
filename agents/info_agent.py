"""
Info Agent Module
=================

Responsible for retrieving relevant notes and stored information from
Firestore that relate to the meeting topic. Summarizes findings to
provide context for meeting preparation.

Workflow:
    1. Receives a meeting topic or description
    2. Queries Firestore for related notes using the retrieve_meeting_notes tool
    3. Summarizes the retrieved information into a concise notes_summary

The agent is defined as an ADK LlmAgent with a Firestore query tool.
"""

import logging
import os

from google.adk.agents import LlmAgent

from database.firestore_client import retrieve_notes

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notes retrieval tool (exposed to the agent)
# ---------------------------------------------------------------------------


def retrieve_meeting_notes(topic: str) -> dict:
    """
    Retrieve notes from Firestore related to a specific meeting topic.

    Searches the meeting_notes collection for documents tagged with
    keywords matching the given topic.

    Args:
        topic: The meeting topic or keyword to search for.

    Returns:
        Dictionary with retrieved notes and metadata.
    """
    logger.info("retrieve_meeting_notes called for topic: %s", topic)

    notes = retrieve_notes(topic)

    if notes:
        # Compile note contents into a summary-ready format
        note_contents = []
        for note in notes:
            note_contents.append(
                f"• {note['title']}: {note['content']}"
            )
        combined_content = "\n".join(note_contents)
    else:
        combined_content = (
            "No stored notes found for this topic. "
            "Consider creating notes for future reference."
        )

    return {
        "status": "notes_retrieved",
        "topic": topic,
        "notes_count": len(notes),
        "content": combined_content,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")

INFO_AGENT_INSTRUCTION = """You are an Information Retrieval Agent specialized in finding relevant meeting context.

Your role is to search for and summarize relevant notes, documents, and information
that will help someone prepare for their meeting.

When given a meeting topic, you MUST:
1. Use the retrieve_meeting_notes tool to search Firestore for relevant information
2. Extract the most important keywords from the meeting description to use as search topics
3. Summarize the retrieved information concisely

IMPORTANT: You MUST respond with ONLY a valid JSON object in this exact format:
{
    "notes_summary": "A concise summary of all relevant notes and information found."
}

Guidelines:
- Focus on extracting key facts, metrics, and action items from notes
- If no notes are found, provide a helpful message suggesting what to prepare
- Keep the summary concise but informative (2-4 sentences)
- Highlight any critical data points or deadlines found in the notes

Do NOT include any text outside the JSON object. Only output the JSON."""

info_agent = LlmAgent(
    model=MODEL_ID,
    name="info_agent",
    description=(
        "Retrieves and summarizes relevant notes from Firestore. "
        "Provides context and background information for meeting preparation."
    ),
    instruction=INFO_AGENT_INSTRUCTION,
    tools=[retrieve_meeting_notes],
)
