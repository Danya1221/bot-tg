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

TEMPLATES_DIR = "templates"
MESSAGES_FILE = "messages.json"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


def is_admin(message: Message):
    return message.from_user and message.from_user.id == ADMIN_ID


def ensure_dirs():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)


def template_path(name):
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    return os.path.join(TEMPLATES_DIR, f"{safe_name}.html")


def save_template(name, text):
    ensure_dirs()
    with open(template_path(name), "w", encoding="utf-8") as f:
        f.write(text)


def load_template(name):
    path = template_path(name)
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_messages():
    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_messages(data):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_message_id(name):
    return load_messages().get(name)


def save_message_id(name, message_id):
    data = load_messages()
    data[name] = message_id
    save_messages(data)


def format_price(value):
    value = value.strip().lower()

    if value in ["off", "нет", "no", "0", "-", "x"]:
        return "❌"

    value = re.sub(r"\D", "", value)

    if not value:
        return "❌"

    return f"{int(value):,}".replace(",", ".") + "₽"


async def publish_to_channel(name, text):
    message_id = get_message_id(name)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            return
        except Exception as e:
            print("Edit error:", e)

    msg = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

    save_message_id(name, msg.message_id)


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот работает ✅\n\n"
        "Команды:\n"
        "/template имя + текст — сохранить шаблон\n"
        "/update имя — обновить пост\n"
        "/prices имя — обновить цены\n"
        "/show имя — показать шаблон\n"
        "/templates — список шаблонов\n"
        "/myid",
        parse_mode=ParseMode.HTML
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

    raw = message.text.replace("/template", "", 1).strip()

    if not raw:
        return await message.answer(
            "Формат:\n\n"
            "/template iphone17\n"
            "твой прайс"
        )

    lines = raw.splitlines()
    name = lines[0].strip()
    text = "\n".join(lines[1:]).strip()

    if not name or not text:
        return await message.answer(
            "Формат:\n\n"
            "/template iphone17\n"
            "твой прайс"
        )

    save_template(name, text)

    await message.answer(
        f"Шаблон <code>{name}</code> сохранён ✅",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("update"))
async def update_template(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    name = message.text.replace("/update", "", 1).strip()

    if not name:
        return await message.answer("Формат: /update iphone17")

    template = load_template(name)

    if not template:
        return await message.answer("Такой шаблон не найден.")

    await publish_to_channel(name, template)

    await message.answer(
        f"Пост <code>{name}</code> обновлён ✅",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("show"))
async def show_template(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    name = message.text.replace("/show", "", 1).strip()

    if not name:
        return await message.answer("Формат: /show iphone17")

    template = load_template(name)

    if not template:
        return await message.answer("Такой шаблон не найден.")

    await message.answer(
        template,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


@dp.message(Command("templates"))
async def templates_list(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    ensure_dirs()

    files = [
        f.replace(".html", "")
        for f in os.listdir(TEMPLATES_DIR)
        if f.endswith(".html")
    ]

    if not files:
        return await message.answer("Шаблонов пока нет.")

    await message.answer("Шаблоны:\n" + "\n".join(files))


@dp.message(Command("prices"))
async def update_prices(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    raw = message.html_text.replace("/template", "", 1).strip()

    if not raw:
        return await message.answer(
            "Формат:\n\n"
            "/prices iphone17\n"
            "iPhone 17 256GB Global Blue = 66600\n"
            "iPhone 17 256GB Global Sage = off"
        )

    lines = raw.splitlines()
    name = lines[0].strip()
    price_lines = lines[1:]

    template = load_template(name)

    if not template:
        return await message.answer("Такой шаблон не найден.")

    updated = template
    changed = 0

    for line in price_lines:
        if "=" not in line:
            continue

        product_name, price = line.split("=", 1)
        product_name = product_name.strip()
        new_price = format_price(price)

        pattern = re.compile(
            rf"(?m)(.*?{re.escape(product_name)}.*?—\s*)([^<\n\r]+)"
        )

        updated, count = pattern.subn(
            rf"\g<1>{new_price}",
            updated,
            count=1
        )

        changed += count

    save_template(name, updated)
    await publish_to_channel(name, updated)

    await message.answer(
        f"Цены обновлены ✅\n"
        f"Шаблон: <code>{name}</code>\n"
        f"Изменено строк: {changed}",
        parse_mode=ParseMode.HTML
    )


async def main():
    ensure_dirs()
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
