"""Structured help entries for the webapp Help tab.

The Help tab is a lightweight learning surface. Keep entries short and focused
so the UI remains scannable and each answer can render without truncation.
"""

from __future__ import annotations


def get_help_entries() -> list[dict[str, str]]:
    """Return ordered Help tab Q&A entries.

    Returns:
        List of dictionaries with ``question`` and ``answer`` keys.
    """
    return [
        {
            "question": "What is an API?",
            "answer": (
                "An API (Application Programming Interface) is a contract for how software "
                "systems talk to each other. In this app, the API is the set of HTTP endpoints "
                "under /api that let you import data and generate names programmatically."
            ),
        },
        {
            "question": "What is cURL and why use it?",
            "answer": (
                "cURL is a command-line tool for making HTTP requests. It's useful for quick "
                "testing and for documenting example requests that you can paste into scripts or "
                "terminal sessions."
            ),
        },
        {
            "question": "What does POST mean?",
            "answer": (
                "POST is an HTTP method used when you send a request body to the server. For example, "
                "generating names uses POST because you submit a JSON payload describing the "
                "class, package, syllable mode, and other options."
            ),
        },
    ]


__all__ = ["get_help_entries"]
