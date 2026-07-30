from __future__ import annotations

import json
import os
import random
import re
import time
from typing import Any

from dotenv import load_dotenv

_HERE = os.path.dirname(__file__)

# override=True: giá trị trong .env thắng biến môi trường cũ còn sót trong shell
load_dotenv(dotenv_path=os.path.join(_HERE, "..", ".env"), override=True)
load_dotenv(dotenv_path=os.path.join(_HERE, "..", "..", ".env"), override=False)
load_dotenv(override=False)


def resolve_mode() -> str:
    forced = (os.getenv("LEARNING_ENGINE_MODE") or "auto").strip().lower()
    if forced in {"gemini", "openai", "mock"}:
        return forced
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "mock"


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def call_llm_json(system: str, user: str) -> tuple[dict[str, Any], str]:
    """Return (parsed_json, provider_name). Raises on hard failure before mock."""
    mode = resolve_mode()
    if mode == "gemini":
        return _call_gemini(system, user), "gemini"
    if mode == "openai":
        return _call_openai(system, user), "openai"
    if mode == "auto":
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            return _call_gemini(system, user), "gemini"
        if os.getenv("OPENAI_API_KEY"):
            return _call_openai(system, user), "openai"
    raise RuntimeError("No LLM provider configured (set GEMINI_API_KEY or OPENAI_API_KEY)")


def _gemini_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY missing")
    return api_key


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "rate limit" in text.lower()


def _retry_attempts() -> int:
    try:
        return max(1, int(os.getenv("LLM_MAX_ATTEMPTS", "4")))
    except ValueError:
        return 4


def _gemini_generate(system: str, user: str, json_mode: bool) -> str:
    """Gọi Gemini qua SDK google-genai, retry backoff khi bị 429 (free tier)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_gemini_key())
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    config: dict[str, Any] = {"system_instruction": system}
    if json_mode:
        config["response_mime_type"] = "application/json"
    # Gemini 3.x khuyến nghị giữ temperature mặc định
    if not model_name.startswith("gemini-3"):
        config["temperature"] = 0.2 if json_mode else 0.4

    attempts = _retry_attempts()
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=user,
                config=types.GenerateContentConfig(**config),
            )
            return resp.text or ""
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_rate_limit(exc) or attempt == attempts - 1:
                raise
            time.sleep(min(2**attempt * 4, 30) + random.uniform(0, 1.5))
    raise last_exc  # type: ignore[misc]


def _call_gemini(system: str, user: str) -> dict[str, Any]:
    return _extract_json(_gemini_generate(system, user, json_mode=True))


def _call_openai(system: str, user: str) -> dict[str, Any]:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    return _extract_json(content)


def call_llm_text(system: str, user: str) -> tuple[str, str]:
    mode = resolve_mode()
    if mode == "mock" or (
        mode == "auto"
        and not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY"))
    ):
        raise RuntimeError("No LLM for text generation")

    if mode in {"gemini", "auto"} and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        return _gemini_generate(system, user, json_mode=False).strip(), "gemini"

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip(), "openai"
