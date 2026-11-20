"""Pure wording and timing for the Save result shown beside the footer. No Tkinter."""
from __future__ import annotations


def save_feedback_text(
    outcome: str, name: str = "", version: int | None = None,
    note: str = "", error: str = "",
) -> str:
    """Plain-English words shown beside Save version. Outcome: saved, unchanged or failed."""
    if outcome == "saved":
        text = f"Saved {name} · version {version}."
        if note.strip():
            text += f" Version note: {note.strip()}"
        return text
    if outcome == "unchanged":
        return f"Nothing to save. {name} is already saved as version {version}."
    if outcome == "failed":
        return f"Not saved. {error.strip() or 'Something went wrong. Try again.'}"
    raise ValueError("Unknown save outcome: " + outcome)


SAVE_FEEDBACK_COLORS = {"saved": "#1e6b34", "unchanged": "#555555", "failed": "#b00020"}
SAVE_FEEDBACK_SECONDS = 6
