"""Unit tests for hiredar.llm.client chat_complete and embed wrappers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from hiredar.llm import chat_complete, embed


class _FakeChoice(SimpleNamespace):
    pass


class _FakeResponse(SimpleNamespace):
    pass


class _FakeChat(SimpleNamespace):
    def completions(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        raise RuntimeError("Should not be called")


class _FakeClient:
    """Mimic minimal subset of openai.OpenAI used by wrappers."""

    def __init__(self) -> None:
        self.called_with: dict[str, Any] | None = None

        class _Completions:
            def __init__(self, outer: _FakeClient):
                self._outer = outer

            def create(self, *args: Any, **kwargs: Any):  # type: ignore
                self._outer.called_with = kwargs
                fake_choice = _FakeChoice(message=SimpleNamespace(content="hello"))
                return _FakeResponse(choices=[fake_choice])

        class _Chat(SimpleNamespace):
            pass

        chat = _Chat()
        chat.completions = _Completions(self)  # type: ignore[attr-defined]
        self.chat = chat

        class _Embeddings:
            def __init__(self, outer: _FakeClient):
                self._outer = outer

            def create(self, *, input, model, timeout=60, **kwargs):  # type: ignore
                self._outer.called_with = {"input": input, "model": model}
                # return shape similar to OpenAI v1
                return _FakeResponse(data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])])

        self.embeddings = _Embeddings(self)


@pytest.fixture(autouse=True)
def patch_client(monkeypatch):
    from hiredar.llm import client as llm_client

    fake_client = _FakeClient()
    monkeypatch.setattr(llm_client, "get_client", lambda: fake_client)
    yield


def test_chat_complete_returns_content():
    content = chat_complete(messages=[], model="gpt-test")
    assert content == "hello"


def test_embed_returns_vectors():
    vectors = embed(["a", "b"], model="embed-test")
    assert vectors == [[0.1, 0.2, 0.3]]
