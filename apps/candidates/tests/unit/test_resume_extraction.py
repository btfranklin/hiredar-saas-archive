from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from apps.candidates.services.resume_processing import extraction


class DummyCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_extract_text_from_pdf_uses_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        extraction,
        "_run_subprocess_extractor",
        lambda mode, path, timeout=None: ("pdf text", None),
    )

    result = extraction.extract_text_from_pdf("resume.pdf")
    assert result == "pdf text"


def test_extract_text_from_pdf_falls_back_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        extraction,
        "_run_subprocess_extractor",
        lambda mode, path, timeout=None: (None, "boom"),
    )
    monkeypatch.setattr(
        extraction,
        "extract_pdf_text",
        lambda path: ("inline text", None),
    )

    result = extraction.extract_text_from_pdf("resume.pdf")
    assert result == "inline text"


def test_extract_text_reads_plain_text(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.txt"
    file_path.write_text(" sample text ")

    result = extraction.extract_text(str(file_path))
    assert result == "sample text"


def test_extract_text_unstructured_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(mode: str, path: str, timeout: int | None = None) -> tuple[str | None, str | None]:
        captured["mode"] = mode
        captured["path"] = path
        captured["timeout"] = timeout
        return ("doc text", None)

    monkeypatch.setattr(extraction, "_run_subprocess_extractor", fake_run)

    result = extraction.extract_text("resume.docx")
    assert result == "doc text"
    assert captured["mode"] == "unstructured"
    assert captured["path"].endswith("resume.docx")


def test_extract_text_unstructured_pdf_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_run(mode: str, path: str, timeout: int | None = None) -> tuple[str | None, str | None]:
        calls.append(mode)
        return (None, "failed")

    monkeypatch.setattr(extraction, "_run_subprocess_extractor", fake_run)
    monkeypatch.setattr(
        extraction,
        "extract_text_from_pdf",
        lambda path: "pdf fallback",
    )

    result = extraction._extract_text_with_unstructured("resume.pdf")
    assert result == "pdf fallback"
    assert calls == ["unstructured"]


def test_run_subprocess_extractor_parses_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"status": "success", "text": "hello"}

    def fake_run(*args: Any, **kwargs: Any) -> DummyCompletedProcess:
        return DummyCompletedProcess(returncode=0, stdout=json.dumps(payload))

    monkeypatch.setattr(extraction.subprocess, "run", fake_run)  # type: ignore[attr-defined]

    text, error = extraction._run_subprocess_extractor("pdf", "resume.pdf", timeout=5)
    assert text == "hello"
    assert error is None


def test_run_subprocess_extractor_handles_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"status": "error", "error": "boom"}

    def fake_run(*args: Any, **kwargs: Any) -> DummyCompletedProcess:
        return DummyCompletedProcess(returncode=1, stdout=json.dumps(payload))

    monkeypatch.setattr(extraction.subprocess, "run", fake_run)  # type: ignore[attr-defined]

    text, error = extraction._run_subprocess_extractor("pdf", "resume.pdf", timeout=5)
    assert text is None
    assert error == "boom"
