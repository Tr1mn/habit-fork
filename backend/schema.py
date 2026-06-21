"""Контракты данных между фронтом, LLM и движком скоринга.

Поток:
    [str, ...]  --LLM-->  Parsed{habits, clash, scenes}  --scoring-->  score+drivers
                                                          --images--->  диптих
    всё вместе --> AnalyzeResponse --> фронт
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

Category = Literal["good", "neutral", "bad"]


class HabitItem(BaseModel):
    text: str
    category: Category
    rank: int = Field(ge=1, le=10)  # 1 = слабое влияние, 10 = критическое


class Parsed(BaseModel):
    """То, что возвращает LLM-проход (или эвристика-фолбэк)."""
    habits: list[HabitItem]
    clash: str = ""               # один Habit Clash, пустая строка = не найден
    continue_scene: str = ""      # англ. промпт сцены "если продолжишь"
    change_scene: str = ""        # англ. промпт сцены "если изменишь 3 привычки"


class Driver(BaseModel):
    dir: Literal["up", "down"]
    text: str


class AnalyzeRequest(BaseModel):
    habits: list[str]


class AnalyzeResponse(BaseModel):
    score: int
    drivers: list[Driver]
    clash: str
    change: list[str]                  # 3 привычки на замену
    scene_bad: str                     # человекочитаемая подпись сцены
    scene_good: str
    image_bad: Optional[str] = None    # data:image/png;base64,... или None
    image_good: Optional[str] = None
    source: Literal["ai", "mock"]      # реальный LLM или эвристика
