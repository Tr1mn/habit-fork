"""Детерминированный движок скоринга (подход B).

Число воспроизводимо и показываемо — на вопрос судьи "откуда 64?" есть ответ:
    score = 50 + Σ(good.rank * 1.1) - Σ(bad.rank * 1.3),  затем clamp 2..98

Никакого ML. Вход — категоризированные привычки от LLM. Выход — число, драйверы
(видимое "почему") и 3 привычки на замену.

    habits ──► [ + хорошие * 1.1 ]──┐
               [ − плохие  * 1.3 ]──┼──► clamp(2..98) ──► score
                                    │
               top-2 good / top-2 bad ──► drivers (▲/▼)
               worst-3 bad           ──► change[]
"""
from __future__ import annotations

from .schema import HabitItem, Driver

GOOD_W = 1.1
BAD_W = 1.3
BASELINE = 50.0

# подсказки на замену, если плохих привычек меньше трёх
_SUGGESTIONS = [
    "добавь спорт 3×/нед",
    "ложись до 23:00",
    "читай 15 минут в день",
    "убери скролл перед сном",
]


def _short(text: str, n: int = 26) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def score_habits(habits: list[HabitItem]) -> tuple[int, list[Driver], list[str]]:
    raw = BASELINE
    for h in habits:
        if h.category == "good":
            raw += h.rank * GOOD_W
        elif h.category == "bad":
            raw -= h.rank * BAD_W
    score = max(2, min(98, round(raw)))

    goods = sorted((h for h in habits if h.category == "good"), key=lambda h: -h.rank)
    bads = sorted((h for h in habits if h.category == "bad"), key=lambda h: -h.rank)

    drivers: list[Driver] = []
    for h in goods[:2]:
        drivers.append(Driver(dir="up", text=_short(h.text)))
    for h in bads[:2]:
        drivers.append(Driver(dir="down", text=_short(h.text)))
    if not drivers:
        drivers.append(Driver(dir="up", text="нейтральный набор привычек"))

    change = [_short(h.text) for h in bads[:3]]
    i = 0
    while len(change) < 3:
        cand = _SUGGESTIONS[i % len(_SUGGESTIONS)]
        if cand not in change:
            change.append(cand)
        i += 1

    return score, drivers, change
