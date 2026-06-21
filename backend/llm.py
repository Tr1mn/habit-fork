"""LLM-проход: разбор привычек + Habit Clash + промпты сцен.

Если есть ANTHROPIC_API_KEY — зовём Claude. Иначе — эвристика-фолбэк, чтобы
приложение всегда отвечало (и страница не падала на демо без ключей).

Anthropic-часть и эвристика возвращают один и тот же контракт `Parsed`.
Чтобы переключиться на OpenAI — поменяй только тело _call_claude.
"""
from __future__ import annotations

import os

from .schema import Parsed
from . import prompts

MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")


def has_llm() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _call_claude(habits: list[str]) -> Parsed:
    import anthropic  # импорт внутри — не нужен, если работаем на моке

    client = anthropic.Anthropic()  # ключ берётся из ANTHROPIC_API_KEY
    habits_block = "\n".join(f"- {h}" for h in habits)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=prompts.SYSTEM,
        messages=[{"role": "user", "content": prompts.USER_TEMPLATE.format(habits_block=habits_block)}],
    )
    raw = "".join(block.text for block in msg.content if block.type == "text")
    data = prompts.extract_json(raw)
    return Parsed.model_validate(data)


def parse_habits(habits: list[str]) -> tuple[Parsed, str]:
    """Возвращает (Parsed, source) где source = 'ai' | 'mock'."""
    if has_llm():
        try:
            return _call_claude(habits), "ai"
        except Exception as e:  # сеть/ключ/кривой JSON — не валим демо
            print(f"[llm] fallback to heuristic: {e}")
    return prompts.heuristic_parse(habits), "mock"
