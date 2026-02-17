"""Groq Llama 3 integration for AI-based validation."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def _build_prompt(
    knowledge: dict[str, Any],
    reference: dict[str, Any],
) -> list[dict[str, str]]:
    """Build the chat messages for the Groq API request."""
    system = (
        "You are a knowledge validation assistant. "
        "Given a knowledge base and reference policies, produce a clear validation output. "
        "Return a concise report with: (1) coherence/alignment summary, "
        "(2) inconsistencies/duplicates/obsolete info, "
        "(3) clarification questions. "
        "Plain text is allowed; do not force JSON."
    )
    user = (
        "Knowledge base JSON:\n"
        + json.dumps(knowledge, indent=2, ensure_ascii=True)
        + "\n\nReference policies JSON:\n"
        + json.dumps(reference, indent=2, ensure_ascii=True)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_validation_text(
    knowledge: dict[str, Any],
    reference: dict[str, Any],
) -> str:
    """Call Groq to generate AI-based validation output as text."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    payload = {
        "model": MODEL,
        "temperature": 0.2,
        "max_tokens": 800,
        "messages": _build_prompt(knowledge, reference),
    }

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(GROQ_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        text = getattr(exc.response, "text", "")
        detail = f"Groq API request failed"
        if status:
            detail += f" (status {status})"
        if text:
            detail += f": {text}"
        raise RuntimeError(detail) from exc
    except ValueError as exc:
        raise RuntimeError("Groq API response was not valid JSON") from exc

    try:
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Groq response is empty")
        return content.strip()
    except KeyError as exc:
        raise RuntimeError("Groq response parsing failed") from exc
