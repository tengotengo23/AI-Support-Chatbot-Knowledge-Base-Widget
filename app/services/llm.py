"""Minimal LLM clients (Anthropic, OpenAI-compatible, Ollama) over plain HTTP."""

from __future__ import annotations

import httpx

from app.config import Settings

MAX_TOKENS = 700


class LLMError(RuntimeError):
    pass


def _post(url: str, *, headers: dict | None = None, json: dict, timeout: float = 60.0) -> dict:
    try:
        resp = httpx.post(url, headers=headers, json=json, timeout=timeout)
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise LLMError(f"LLM HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _alternate(messages: list[dict]) -> list[dict]:
    """Merge consecutive same-role turns and make sure the list starts with a user turn."""
    out: list[dict] = []
    for m in messages:
        if out and out[-1]["role"] == m["role"]:
            out[-1] = {"role": m["role"], "content": out[-1]["content"] + "\n\n" + m["content"]}
        else:
            out.append({"role": m["role"], "content": m["content"]})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def complete(system: str, messages: list[dict], settings: Settings) -> str:
    """messages: [{"role": "user"|"assistant", "content": str}], last one from the user."""
    messages = _alternate(messages)
    if not messages:
        raise LLMError("No user message")
    provider = settings.llm_provider

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        data = _post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": MAX_TOKENS,
                "system": system,
                "messages": messages,
            },
        )
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()

    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        data = _post(
            f"{settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "max_completion_tokens": MAX_TOKENS,
                "messages": [{"role": "system", "content": system}, *messages],
            },
        )
        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected OpenAI response") from exc

    if provider == "ollama":
        data = _post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "stream": False,
                "options": {"temperature": 0.2},
                "messages": [{"role": "system", "content": system}, *messages],
            },
            timeout=180.0,
        )
        return (data.get("message", {}).get("content") or "").strip()

    raise LLMError(f"Unknown LLM provider: {provider}")
