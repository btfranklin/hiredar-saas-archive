"""
Utility helpers for working with Promptdown prompt files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from promptdown import StructuredPrompt
from promptdown.types import ResponsesMessage  # type: ignore


def load_structured_prompt(
    path: str | Path,
    variables: Mapping[str, Any] | None = None,
) -> Sequence[ResponsesMessage]:
    """Load a Promptdown file and apply template variables, returning Responses input."""

    prompt_path = Path(path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    structured = StructuredPrompt.from_promptdown_file(str(prompt_path))
    if variables:
        structured.apply_template_values(dict(variables))

    return structured.to_responses_input()
