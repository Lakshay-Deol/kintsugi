"""LLM adapter — OpenAI-compatible interface for Gemma via Google AI Studio.

Gemma 3 does not reliably support system prompts — fold all instructions
into the user turn. No reliable JSON mode — parse defensively with 1 retry.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import openai

from kintsugi.config import get_config

log = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMRateLimitError(LLMError):
    pass


def _build_client() -> openai.OpenAI:
    cfg = get_config()
    return openai.OpenAI(
        api_key=cfg.llm_api_key,
        base_url=cfg.llm_base_url,
        timeout=cfg.llm_timeout_seconds,
        max_retries=0,  # we handle retries manually
    )


def complete(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.1,
) -> str:
    """
    Send a completion request. Gemma 3: fold system into user turn.
    Retries up to cfg.llm_max_attempts on transient errors (429/5xx).
    """
    cfg = get_config()
    client = _build_client()
    mdl = model or cfg.llm_model
    mtok = max_tokens or cfg.llm_max_tokens

    # Gemma 3 system-prompt workaround: fold into user turn
    if system:
        user_content = f"[Instructions]\n{system}\n\n[Question]\n{prompt}"
    else:
        user_content = prompt

    messages = [{"role": "user", "content": user_content}]

    last_exc: Exception | None = None
    for attempt in range(1, cfg.llm_max_attempts + 1):
        try:
            resp = client.chat.completions.create(
                model=mdl,
                messages=messages,
                max_tokens=mtok,
                temperature=temperature,
            )
            text = resp.choices[0].message.content or ""
            log.info(
                "LLM call ok model=%s tokens_in=%s tokens_out=%s attempt=%d",
                mdl,
                resp.usage.prompt_tokens if resp.usage else "?",
                resp.usage.completion_tokens if resp.usage else "?",
                attempt,
            )
            return text.strip()
        except openai.APITimeoutError as exc:
            last_exc = exc
            log.warning("LLM timeout attempt=%d/%d", attempt, cfg.llm_max_attempts)
        except openai.RateLimitError as exc:
            last_exc = exc
            log.warning("LLM rate limit attempt=%d/%d", attempt, cfg.llm_max_attempts)
            if attempt < cfg.llm_max_attempts:
                time.sleep(cfg.llm_retry_base_seconds * (2 ** (attempt - 1)))
        except openai.APIStatusError as exc:
            last_exc = exc
            if exc.status_code and exc.status_code >= 500:
                log.warning("LLM 5xx attempt=%d/%d: %s", attempt, cfg.llm_max_attempts, exc)
                if attempt < cfg.llm_max_attempts:
                    time.sleep(cfg.llm_retry_base_seconds)
            else:
                raise LLMError(f"LLM API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected LLM error: {exc}") from exc

    if isinstance(last_exc, openai.APITimeoutError):
        raise LLMTimeoutError("LLM timed out after all attempts") from last_exc
    if isinstance(last_exc, openai.RateLimitError):
        raise LLMRateLimitError("LLM rate limited after all attempts") from last_exc
    raise LLMError(f"LLM failed after {cfg.llm_max_attempts} attempts") from last_exc


def complete_json(prompt: str, *, system: str | None = None) -> dict[str, Any] | None:
    """
    Request structured JSON output. Parse defensively with 1 retry.
    Returns None if parsing fails after retry (caller shows verbatim fallback).
    """
    for attempt in range(1, 3):  # max 1 retry
        text = complete(prompt, system=system)
        # Try to extract JSON from fenced block or raw
        candidate = text
        if "```" in text:
            import re
            m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
            if m:
                candidate = m.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            log.warning("JSON parse failed attempt=%d, text=%r", attempt, text[:200])
    return None
