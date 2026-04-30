import asyncio
import json
import os
import re

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = "@Netizenshop"
ADMIN_ID = 707131428

TEMPLATE_FILE = "template.html"
MESSAGE_FILE = "message.json"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


def is_admin(message: Message):
    return message.from_user and message.from_user.id == ADMIN_ID


def save_template(text):
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        f.write(text)


def load_template():
    if not os.path.exists(TEMPLATE_FILE):
        return None

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def save_message_id(message_id):
    with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id}, f)


def load_message_id():
    try:
        with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("message_id")
    except Exception:
        return None


def format_price(value):
    value = value.strip().lower()

    if value in ["off", "нет", "no", "0", "-", "x"]:
        return "❌"

    value = re.sub(r"\D", "", value)

    if not value:
        return "❌"

    return f"{int(value):,}".replace(",", ".") + "₽"


async def publish_to_channel(text):
    message_id = load_message_id()

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            return
        except Exception as e:
            print("Edit error:", e)

    msg = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode=ParseMode.HTML
    )

    save_message_id(msg.message_id)


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот работает ✅\n\n"
        "Команды:\n"
        "/template + текст — сохранить шаблон\n"
        "/prices — обновить цены пачкой\n"
        "/show — показать шаблон\n"
        "/update — обновить канал\n"
        "/myid"
    )


@dp.message(Command("myid"))
async def myid(message: Message):
    await message.answer(
        f"Твой Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("template"))
async def set_template(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    text = message.html_text.replace("/template", "", 1).strip()

    if not text:
        return await message.answer("Пришли текст после команды /template")

    save_template(text)
    await message.answer("Шаблон сохранён ✅")


@dp.message(Command("show"))
async def show_template(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    template = load_template()

    if not template:
        return await message.answer("Шаблон ещё не сохранён.")

    await message.answer(template, parse_mode=ParseMode.HTML)


@dp.message(Command("update"))
async def update_channel(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    template = load_template()

    if not template:
        return await message.answer("Сначала сохрани шаблон через /template.")

    await publish_to_channel(template)
    await message.answer("Канал обновлён ✅")


@dp.message(Command("prices"))
async def update_prices(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    template = load_template()

    if not template:
        return await message.answer("Сначала сохрани шаблон через /template.")

    raw = message.text.replace("/prices", "", 1).strip()

    if not raw:
        return await message.answer(
            "Формат:\n\n"
            "/prices\n"
            "iPhone 17 256GB Global Blue = 66600\n"
            "iPhone 17 256GB Global Sage = off"
        )

    updated = template
    changed = 0

    for line in raw.splitlines():
        if "=" not in line:
            continue

        name, price = line.split("=", 1)
        name = name.strip()
        new_price = format_price(price)

        pattern = re.compile(
            rf"(?m)(^.*?{re.escape(name)}.*?—\s*)([^<\n\r]+)"
        )

        updated, count = pattern.subn(
            rf"\g<1>{new_price}",
            updated,
            count=1
        )

        changed += count

    save_template(updated)
    await publish_to_channel(updated)

    await message.answer(f"Цены обновлены ✅\nИзменено строк: {changed}")


async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
