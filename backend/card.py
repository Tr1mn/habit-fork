"""Склейка диптиха в одну шерибельную PNG-карточку (Pillow).

Это шер-артефакт: когда его форвардят в Telegram, он самодостаточен — число,
обе сцены будущего, конфликт и 3 привычки на замену прямо на картинке.

  ┌──────────────────────────────────────┐
  │ ТЫ ЧЕРЕЗ 10 ЛЕТ            47/100      │
  │ проекция AI                           │
  │ ┌─────────────┐ ┌─────────────┐       │
  │ │ продолжишь  │ │ изменишь 3  │       │
  │ │  (тёмное)   │ │  (светлое)  │       │
  │ └─────────────┘ └─────────────┘       │
  │ Конфликт: хочешь копить, но тратишь   │
  │ Измени: тикток · траты · поздний сон  │
  │                        @HabitForkBot  │
  └──────────────────────────────────────┘

Без реальных картинок (нет HF_TOKEN) рисуем плейсхолдер-плитки — карточка всё равно
собирается. Emoji в PIL не рендерятся (arial), поэтому на картинке только текст;
эмодзи живут в подписи Telegram-сообщения.
"""
from __future__ import annotations

import base64
import io

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1350
PAD = 48
PANEL_TOP = 210
PANEL_H = 640
GAP = 16

BG = (12, 13, 18)
TXT = (238, 240, 246)
MUTED = (130, 136, 152)
GOOD_C = (93, 202, 165)
DARK_TILE = (20, 18, 22)
GOOD_TILE = (22, 48, 42)

_FONT_PATHS = {
    False: ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "arial.ttf"],
    True: ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf"],
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for p in _FONT_PATHS[bold]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _score_color(score: int) -> tuple[int, int, int]:
    if score < 45:
        return (216, 90, 48)
    if score < 65:
        return (239, 159, 39)
    return (29, 158, 117)


def _decode(data_url: str | None) -> Image.Image | None:
    if not data_url:
        return None
    try:
        b64 = data_url.split(",", 1)[-1]
        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    except Exception:
        return None


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def compose(img_bad, img_good, score: int, clash: str, change: list[str]) -> bytes:
    card = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(card)

    # header
    d.text((PAD, 48), "ТЫ ЧЕРЕЗ 10 ЛЕТ", font=_font(46, True), fill=TXT)
    d.text((PAD, 110), "проекция AI · зеркало привычек", font=_font(26), fill=MUTED)

    # score (справа)
    sfont = _font(92, True)
    stext = str(score)
    sw = d.textlength(stext, font=sfont)
    d.text((W - PAD - sw, 50), stext, font=sfont, fill=_score_color(score))
    of = _font(28)
    d.text((W - PAD - sw - d.textlength("/100", font=of) - 8, 110), "/100", font=of, fill=MUTED)

    # диптих
    half = (W - PAD * 2 - GAP) // 2
    left = _decode(img_bad) or Image.new("RGB", (half, PANEL_H), DARK_TILE)
    right = _decode(img_good) or Image.new("RGB", (half, PANEL_H), GOOD_TILE)
    left = ImageOps.fit(left, (half, PANEL_H), method=Image.LANCZOS)
    right = ImageOps.fit(right, (half, PANEL_H), method=Image.LANCZOS)
    card.paste(left, (PAD, PANEL_TOP))
    card.paste(right, (PAD + half + GAP, PANEL_TOP))

    # подписи на плитках (тёмная плашка для читаемости)
    lab = _font(26, True)
    for x, text in ((PAD, "ЕСЛИ ПРОДОЛЖИШЬ"), (PAD + half + GAP, "ЕСЛИ ИЗМЕНИШЬ 3")):
        tw = d.textlength(text, font=lab)
        d.rectangle((x, PANEL_TOP, x + tw + 28, PANEL_TOP + 44), fill=(0, 0, 0))
        d.text((x + 14, PANEL_TOP + 9), text, font=lab, fill=TXT)

    # низ: конфликт + что менять
    y = PANEL_TOP + PANEL_H + 36
    body = _font(30)
    if clash:
        d.text((PAD, y), "КОНФЛИКТ", font=_font(24, True), fill=(239, 159, 39))
        y += 38
        for line in _wrap(d, clash, body, W - PAD * 2):
            d.text((PAD, y), line, font=body, fill=TXT)
            y += 40
        y += 14
    if change:
        d.text((PAD, y), "ИЗМЕНИ 3", font=_font(24, True), fill=GOOD_C)
        y += 38
        for line in _wrap(d, " · ".join(change), body, W - PAD * 2):
            d.text((PAD, y), line, font=body, fill=GOOD_C)
            y += 40

    # вотермарка
    wm = _font(26)
    d.text((PAD, H - 56), "@HabitForkBot", font=wm, fill=MUTED)

    out = io.BytesIO()
    card.save(out, "PNG")
    return out.getvalue()
