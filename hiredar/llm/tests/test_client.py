"""Unit tests for hiredar.llm.client chat_complete and embed wrappers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from hiredar.llm import embed, get_llm_response


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
        self.timeout: int | None = None

        class _Responses:
            def __init__(self, outer: _FakeClient):
                self._outer = outer

            def create(self, *args: Any, **kwargs: Any):  # type: ignore
                self._outer.called_with = kwargs
                return _FakeResponse(output_text="hello")

        self.responses = _Responses(self)

        class _Embeddings:
            def __init__(self, outer: _FakeClient):
                self._outer = outer

            def create(self, *, input, model, timeout=60, **kwargs):  # type: ignore  # pylint: disable=redefined-builtin, unused-argument
                self._outer.called_with = {"input": input, "model": model}
                # return shape similar to OpenAI v1
                return _FakeResponse(data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])])

        self.embeddings = _Embeddings(self)

    def with_options(self, **options: Any) -> "_FakeClient":
        self.timeout = options.get("timeout")
        return self


@pytest.fixture(autouse=True)
def patch_client(monkeypatch):
    from hiredar.llm import client as llm_client

    fake_client = _FakeClient()
    monkeypatch.setattr(llm_client, "get_client", lambda: fake_client)
    yield


def test_chat_complete_returns_content():
    content = get_llm_response(response_input=[], model="gpt-test")
    assert content == "hello"


def test_embed_returns_vectors():
    vectors = embed(["a", "b"], model="embed-test")
    assert vectors == [[0.1, 0.2, 0.3]]


def test_chat_complete_passes_reasoning_effort():
    # Call with a reasoning effort and verify it is forwarded to Responses API
    _ = get_llm_response(
        response_input=[
            {"role": "user", "content": [{"type": "input_text", "text": "hi"}]}
        ],
        model="gpt-test",
        reasoning_effort="medium",
    )

    from hiredar.llm import client as llm_client

    fake = cast(Any, llm_client.get_client())
    assert isinstance(fake.called_with, dict)  # pylint: disable=no-member
    reasoning = fake.called_with.get("reasoning")  # pylint: disable=no-member
    assert isinstance(reasoning, dict)
    assert reasoning.get("effort") == "medium"


def test_chat_complete_maps_max_tokens_to_max_output_tokens():
    _ = get_llm_response(
        response_input=[
            {"role": "user", "content": [{"type": "input_text", "text": "hi"}]}
        ],
        model="gpt-test",
        max_tokens=77,
    )

    from hiredar.llm import client as llm_client

    fake = cast(Any, llm_client.get_client())
    assert isinstance(fake.called_with, dict)  # pylint: disable=no-member
    assert fake.called_with.get("max_output_tokens") == 77  # pylint: disable=no-member
    assert "max_tokens" not in fake.called_with  # pylint: disable=no-member


def test_embed_applies_timeout_via_with_options():
    _ = embed(["text"], model="embed-test", timeout=123)

    from hiredar.llm import client as llm_client

    fake = cast(Any, llm_client.get_client())
    assert fake.timeout == 123  # pylint: disable=no-member
