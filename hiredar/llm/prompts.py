"""
Utility helpers for working with Promptdown prompt files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from promptdown import StructuredPrompt


def load_structured_prompt(
    path: str | Path,
    variables: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Load a Promptdown file and apply template variables, returning messages."""

    prompt_path = Path(path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    structured = StructuredPrompt.from_promptdown_file(str(prompt_path))
    if variables:
        structured.apply_template_values(dict(variables))

    return structured.to_chat_completion_messages()
