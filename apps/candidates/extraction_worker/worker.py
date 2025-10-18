"""Standalone entry point for resume extraction subprocesses."""

from __future__ import annotations

import json
import sys
from importlib import import_module
from typing import Any, Callable, Dict, Tuple


def _load_extractors() -> Tuple[
    Callable[[str], Tuple[str | None, str | None]],
    Callable[[str], Tuple[str | None, str | None]],
]:
    module = import_module("apps.candidates.extraction_worker.core")
    return module.extract_pdf_text, module.extract_unstructured_text  # type: ignore[attr-defined]


def _build_payload(
    extractor: Callable[[str], Tuple[str | None, str | None]],
    file_path: str,
) -> Dict[str, Any]:
    text, error = extractor(file_path)
    if text:
        return {"status": "success", "text": text}
    return {"status": "error", "error": error or "Unknown extraction error"}


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        payload = {"status": "error", "error": "Insufficient arguments"}
        print(json.dumps(payload))
        return 1

    mode = argv[1]
    file_path = argv[2]

    extract_pdf_text, extract_unstructured_text = _load_extractors()

    if mode == "pdf":
        payload = _build_payload(extract_pdf_text, file_path)
    elif mode == "unstructured":
        payload = _build_payload(extract_unstructured_text, file_path)
    else:
        payload = {"status": "error", "error": f"Unknown extraction mode '{mode}'"}

    print(json.dumps(payload))
    return 0 if payload.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
