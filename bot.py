"""Habit Fork — Telegram-бот.

Тонкий слой поверх того же бэкенда, что и веб:
    текст с привычками → llm.parse_habits → scoring.score_habits
                       → images.generate_pair → card.compose → фото + подпись

Запуск:  python bot.py   (нужен TELEGRAM_BOT_TOKEN в .env от @BotFather)
"""
from __future__ import annotations

import asyncio
import os
import re

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from backend import card, images, llm, scoring

dp = Dispatcher()

WELCOME = (
    "Привет 👋 Я Habit Fork.\n\n"
    "Пришли свои привычки одним сообщением — через запятую или с новой строки. "
    "Покажу, кем ты станешь через 10 лет, и как это переписать.\n\n"
    "Например:\n"
    "бегаю по утрам, читаю перед сном, скроллю тикток до 2 ночи, коплю на квартиру"
)


def parse_habits_text(text: str) -> list[str]:
    parts = re.split(r"[\n,;]+", text)
    cleaned = [p.strip(" -•—.\t") for p in parts]
    return [p for p in cleaned if p][:20]


def build_caption(score: int, clash: str, change: list[str], source: str) -> str:
    lines = [f"🔮 Ты через 10 лет: {score}/100", "проекция AI, не предсказание"]
    if clash:
        lines.append(f"⚡ {clash}")
    if change:
        lines.append("Измени 3: " + " · ".join(change))
    if source == "mock":
        lines.append("\n(демо-режим: ключи AI не подключены)")
    return "\n".join(lines)


async def _share_url(bot: Bot) -> str | None:
    try:
        me = await bot.me()
        return (
            f"https://t.me/share/url?url=https://t.me/{me.username}"
            "&text=Узнай,%20кем%20ты%20станешь%20через%2010%20лет%20по%20привычкам"
        )
    except Exception:
        return None


def _keyboard(share: str | None) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton(text="🔁 Заново", callback_data="restart")]
    if share:
        row.append(InlineKeyboardButton(text="📤 Поделиться", url=share))
    return InlineKeyboardMarkup(inline_keyboard=[row])


@dp.message(CommandStart())
async def on_start(m: Message):
    await m.answer(WELCOME)


@dp.callback_query(F.data == "restart")
async def on_restart(c: CallbackQuery):
    await c.message.answer("Пришли новые привычки сообщением 👇")
    await c.answer()


@dp.message(F.text)
async def on_habits(m: Message):
    habits = parse_habits_text(m.text)
    if len(habits) < 3:
        await m.answer("Нужно минимум 3 привычки. Пришли их через запятую или списком 👇")
        return
    try:
        await m.bot.send_chat_action(m.chat.id, ChatAction.UPLOAD_PHOTO)
        parsed, source = await asyncio.to_thread(llm.parse_habits, habits)
        score, _drivers, change = scoring.score_habits(parsed.habits)
        img_bad, img_good = await images.generate_pair(parsed.continue_scene, parsed.change_scene, score)
        png = await asyncio.to_thread(card.compose, img_bad, img_good, score, parsed.clash, change)
        photo = BufferedInputFile(png, filename="future.png")
        await m.answer_photo(
            photo,
            caption=build_caption(score, parsed.clash, change, source),
            reply_markup=_keyboard(await _share_url(m.bot)),
        )
    except Exception as e:
        print(f"[bot] error: {e}")
        await m.answer("Упс, что-то пошло не так. Попробуй ещё раз 🙏")


async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Нет TELEGRAM_BOT_TOKEN в .env — возьми токен у @BotFather")
    bot = Bot(token)
    print("Habit Fork bot запущен. Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
