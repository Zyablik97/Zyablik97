from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ROOT_DIR, SUBTOPICS
from .utils import log, read_json, write_json


@dataclass(frozen=True)
class ScriptData:
    topic: str
    hook: str
    body: str
    cta: str
    full_text: str
    keywords: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScriptData":
        keywords = data.get("keywords") or ["science", "space", "nature"]
        full_text = data.get("full_text") or " ".join(
            part.strip() for part in [data.get("hook", ""), data.get("body", ""), data.get("cta", "")] if part
        )
        return cls(
            topic=str(data.get("topic", "Удивительный факт")),
            hook=str(data.get("hook", "")),
            body=str(data.get("body", "")),
            cta=str(data.get("cta", "")),
            full_text=str(full_text),
            keywords=[str(k).strip().lower() for k in keywords][:5],
        )


def _prompt(subtopic: str) -> str:
    system = (ROOT_DIR / "prompts" / "system.md").read_text(encoding="utf-8")
    examples = (ROOT_DIR / "prompts" / "examples.md").read_text(encoding="utf-8")
    return f"{system}\n\nПримеры:\n{examples}\n\nПодтема: {subtopic}. Верни только валидный JSON."


def _load_mock() -> ScriptData:
    return ScriptData.from_dict(json.loads((ROOT_DIR / "tests" / "fixtures" / "sample_script.json").read_text(encoding="utf-8")))


def _generate_with_gemini(subtopic: str) -> ScriptData:
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    schema = {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "hook": {"type": "string"},
            "body": {"type": "string"},
            "cta": {"type": "string"},
            "full_text": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["topic", "hook", "body", "cta", "full_text", "keywords"],
    }
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        _prompt(subtopic),
        generation_config={"response_mime_type": "application/json", "response_schema": schema},
    )
    return ScriptData.from_dict(json.loads(response.text))


def _generate_with_groq(subtopic: str) -> ScriptData:
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": _prompt(subtopic)}],
        temperature=0.9,
    )
    content = completion.choices[0].message.content or "{}"
    return ScriptData.from_dict(json.loads(content))


def _remember_topic(topic: str) -> None:
    path = ROOT_DIR / "state" / "used_topics.json"
    used = read_json(path, [])
    if topic in used:
        used.remove(topic)
    used.append(topic)
    write_json(path, used[-50:])


def generate_script(subtopic: str | None = None) -> ScriptData:
    subtopic = subtopic or random.choice(SUBTOPICS)
    if os.getenv("USE_MOCK_LLM", "0") == "1":
        script = _load_mock()
        _remember_topic(script.topic)
        return script

    used = set(read_json(ROOT_DIR / "state" / "used_topics.json", []))
    last_error: Exception | None = None
    for producer in (_generate_with_gemini, _generate_with_groq):
        for _ in range(3):
            try:
                script = producer(subtopic)
                if script.topic not in used:
                    _remember_topic(script.topic)
                    return script
            except Exception as exc:
                last_error = exc
                log.warning("LLM provider failed: %s", exc)
                break
    if last_error:
        raise last_error
    script = _load_mock()
    _remember_topic(script.topic)
    return script
