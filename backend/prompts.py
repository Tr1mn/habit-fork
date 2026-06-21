"""Промпт для LLM-прохода + эвристика-фолбэк (когда нет ключа).

Один LLM-вызов возвращает JSON-контракт `Parsed`:
  - каждая привычка: {text, category, rank}
  - один Habit Clash (или "")
  - два англоязычных промпта сцен для SDXL (без лиц, только обстановка)
"""
from __future__ import annotations

import json
import re

from .schema import HabitItem, Parsed

SYSTEM = (
    "Ты — движок продукта Habit Fork. Анализируешь привычки человека и возвращаешь "
    "СТРОГО валидный JSON, без markdown, без пояснений. Это проекция/зеркало, не наука."
)

# Просим модель вернуть ровно контракт Parsed.
USER_TEMPLATE = """Привычки человека (свободный текст):
{habits_block}

Верни JSON РОВНО такой формы:
{{
  "habits": [{{"text": "<исходная привычка>", "category": "good|neutral|bad", "rank": 1-10}}],
  "clash": "<одно предложение про конфликт двух привычек, или пустая строка>",
  "continue_scene": "<английский промпт сцены БЕЗ людей и лиц: если человек НЕ изменится, обстановка отражает плохие привычки>",
  "change_scene": "<английский промпт сцены БЕЗ людей и лиц: если изменит 3 ключевые привычки, светлая вдохновляющая обстановка>"
}}

Правила:
- category: good = помогает успеху, bad = вредит, neutral = нейтрально.
- rank: 1 = слабое влияние на жизнь, 10 = критическое.
- clash: ищи противоречие (напр. "хочешь накопить, но тратишь импульсивно"). Если нет — "".
- scene-промпты на английском, описывают ТОЛЬКО обстановку/интерьер/предметы, без людей.
- Верни только JSON."""


# ───────────────────────── эвристика-фолбэк ─────────────────────────

GOOD = ["спорт", "бег", "бега", "зал", "трен", "фитнес", "чтен", "книг", "читаю",
        "медитац", "йог", "сон", "рано", "ранний", "вод", "воду", "овощ", "фрукт",
        "учеб", "учу", "англ", "код", "програм", "проект", "план", "эконом", "копл",
        "накопл", "инвест", "savings", "gym", "run", "read", "sleep", "study",
        "water", "meditat", "walk", "ходьб"]
BAD = ["куре", "курю", "сигарет", "вейп", "алко", "пиво", "выпив", "фастфуд",
       "сахар", "сладк", "прокраст", "поздно", "ночь", "ночью", "импульс", "трат",
       "шоп", "покуп", "долг", "кредит", "азарт", "ставк", "игр", "скролл", "залип",
       "тикток", "инстаг", "ютуб", "сериал", "фид", "smoke", "alcohol", "junk",
       "sugar", "scroll", "procrast", "debt", "gamble", "vape"]


def _classify(text: str) -> HabitItem:
    t = text.lower()
    g = any(k in t for k in GOOD)
    b = any(k in t for k in BAD)
    cat = "good" if (g and not b) else "bad" if b else "neutral"
    base = 3 if cat == "neutral" else 6
    rank = min(10, base + (len(text) % 4))
    return HabitItem(text=text, category=cat, rank=rank)


def _clash(habits: list[HabitItem]) -> str:
    joined = " ".join(h.text.lower() for h in habits)
    if re.search(r"эконом|копл|накопл|инвест|savings", joined) and \
       re.search(r"трат|шоп|покуп|импульс|кредит|долг", joined):
        return "Хочешь накопить, но тратишь импульсивно. Эти две тянут в разные стороны."
    if re.search(r"спорт|бег|зал|сон|вод", joined) and \
       re.search(r"куре|алко|поздно|ночь|фастфуд|сахар", joined):
        return "Заботишься о теле, но добиваешь его курением/недосыпом. Половина усилий впустую."
    goods = [h for h in habits if h.category == "good"]
    bads = [h for h in habits if h.category == "bad"]
    if goods and bads:
        return f"«{goods[0].text}» и «{bads[0].text}» работают друг против друга."
    return "Явных конфликтов мало — но и сильных тянущих вверх привычек не хватает."


def heuristic_parse(habits: list[str]) -> Parsed:
    items = [_classify(h) for h in habits]
    goods = [h for h in items if h.category == "good"]
    bads = [h for h in items if h.category == "bad"]
    bad_hint = bads[0].text if bads else "procrastination"
    good_hint = goods[0].text if goods else "calm and focus"
    return Parsed(
        habits=items,
        clash=_clash(items),
        continue_scene=(
            "dark cluttered messy room, dim lighting, tired neglected interior, "
            "empty bottles and clutter, no people, no face, cinematic, photographic, moody"
        ),
        change_scene=(
            "bright airy modern studio, sunlight, plants, books and sports gear, "
            "clean organized space, no people, no face, cinematic, photographic, hopeful"
        ),
    )


def extract_json(raw: str) -> dict:
    """Достаёт первый JSON-объект из ответа модели (на случай обёрток)."""
    raw = raw.strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError("LLM не вернул JSON")
    return json.loads(m.group(0))
