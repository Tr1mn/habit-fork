"""Генерация диптиха через Hugging Face Inference API (SDXL-Turbo).

Две картинки генерятся ПАРАЛЛЕЛЬНО (asyncio.gather) — это прямой удар по главному
риску демо (латентность). Если HF_TOKEN нет или запрос упал — возвращаем None,
и фронт показывает CSS-плейсхолдер (диптих не ломается).

Интенсивность сцены модулируется числом: низкий score → темнее "продолжишь".
"""
from __future__ import annotations

import asyncio
import base64
import os

import httpx

HF_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/sdxl-turbo")
HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

_STYLE = "no people, no face, environmental, cinematic lighting, highly detailed, 4k"


def has_images() -> bool:
    return bool(os.getenv("HF_TOKEN"))


def _final_prompt(scene: str, score: int, good_side: bool) -> str:
    if good_side:
        mood = "vibrant, warm sunlight, uplifting"
    else:
        # чем ниже score, тем мрачнее
        mood = "very dark and bleak" if score < 35 else "dim and gloomy" if score < 55 else "muted"
    return f"{scene}, {mood}, {_STYLE}"


async def _one(client: httpx.AsyncClient, prompt: str) -> str | None:
    try:
        r = await client.post(
            HF_URL,
            headers={"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"},
            json={"inputs": prompt, "parameters": {"num_inference_steps": 2, "guidance_scale": 0.0}},
            timeout=60,
        )
        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
            print(f"[images] HF {r.status_code}: {r.text[:160]}")
            return None
        b64 = base64.b64encode(r.content).decode()
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[images] error: {e}")
        return None


async def generate_pair(continue_scene: str, change_scene: str, score: int) -> tuple[str | None, str | None]:
    if not has_images():
        return None, None
    async with httpx.AsyncClient() as client:
        bad, good = await asyncio.gather(
            _one(client, _final_prompt(continue_scene, score, good_side=False)),
            _one(client, _final_prompt(change_scene, score, good_side=True)),
        )
    return bad, good
