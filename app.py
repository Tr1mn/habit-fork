"""Habit Fork — бэкенд.

  GET  /              → отдаёт index.html (фронт)
  POST /api/analyze   → {habits:[...]} → score + drivers + clash + диптих

Поток одного запроса:
    habits ─► llm.parse_habits ─► scoring.score_habits ─► images.generate_pair ─► JSON

Запуск:  uvicorn app:app --reload --port 8000   (потом открой http://localhost:8000)
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

load_dotenv()

from backend import llm, images, scoring
from backend.schema import AnalyzeRequest, AnalyzeResponse, Parsed

app = FastAPI(title="Habit Fork")

HERE = os.path.dirname(os.path.abspath(__file__))


def _short(t: str, n: int = 26) -> str:
    return t if len(t) <= n else t[: n - 1] + "…"


def _captions(parsed: Parsed) -> tuple[str, str]:
    bads = [h for h in parsed.habits if h.category == "bad"]
    goods = [h for h in parsed.habits if h.category == "good"]
    bad = f"тёмная комната, {_short(bads[0].text)}, усталость" if bads else "серые будни, прокрастинация"
    good = f"светлая студия, {_short(goods[0].text)}, энергия" if goods else "спокойствие, спорт, ясная голова"
    return bad, good


@app.get("/")
async def index():
    return FileResponse(os.path.join(HERE, "index.html"))


@app.get("/api/health")
async def health():
    return {"ok": True, "llm": llm.has_llm(), "images": images.has_images()}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    parsed, source = await run_in_threadpool(llm.parse_habits, req.habits)
    score, drivers, change = scoring.score_habits(parsed.habits)
    scene_bad, scene_good = _captions(parsed)
    img_bad, img_good = await images.generate_pair(parsed.continue_scene, parsed.change_scene, score)

    return AnalyzeResponse(
        score=score,
        drivers=drivers,
        clash=parsed.clash,
        change=change,
        scene_bad=scene_bad,
        scene_good=scene_good,
        image_bad=img_bad,
        image_good=img_good,
        source=source,
    )
