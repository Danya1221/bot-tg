import asyncio
import json
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@Netizenshop"

ADMIN_ID = 707131428  # сюда потом вставишь свой Telegram ID

DATA_FILE = "prices.json"
MESSAGE_FILE = "message.json"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


def is_admin(message: Message):
    return message.from_user and message.from_user.id == ADMIN_ID


def load_data():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_message_id():
    try:
        with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("message_id")
    except Exception:
        return None


def save_message_id(message_id):
    with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id}, f)


def format_price(price):
    if price is None:
        return "❌"

    price = int(price)
    return f"{price:,}".replace(",", ".") + "₽"


def build_price_text():
    data = load_data()

    if not data:
        return "Прайс пока пуст."

    text = ""

    for category in data:
        text += f"<b>{category['category']}</b>\n\n"

        for item in category["items"]:
            price = format_price(item["price"]) if item["available"] else "❌"
            text += f"📱<code>{item['name']} — {price}</code>\n"

        text += "\n━━━━━━━━━━━━━━\n\n"

    text += (
        "eSIM - только виртуальные\n\n"
        "SIM+eSIM - физическая + виртуальная\n\n"
        "🛒 Для заказа:\n"
        "@netizenstaff"
    )

    return text


async def update_channel_message():
    text = build_price_text()
    message_id = load_message_id()

    try:
        if message_id:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=message_id,
                text=text
            )
        else:
            msg = await bot.send_message(CHANNEL_ID, text)
            save_message_id(msg.message_id)

    except Exception:
        msg = await bot.send_message(CHANNEL_ID, text)
        save_message_id(msg.message_id)


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот работает.\n\n"
        "Команды:\n"
        "/add категория | товар | цена\n"
        "/price товар | цена\n"
        "/off товар\n"
        "/on товар\n"
        "/delete товар\n"
        "/list\n"
        "/update\n"
        "/myid"
    )


@dp.message(Command("myid"))
async def myid(message: Message):
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>")


@dp.message(Command("add"))
async def add_item(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    try:
        text = message.text.replace("/add", "", 1).strip()
        category, name, price = [x.strip() for x in text.split("|")]

        data = load_data()

        for cat in data:
            if cat["category"] == category:
                cat["items"].append({
                    "name": name,
                    "price": int(price),
                    "available": True
                })
                break
        else:
            data.append({
                "category": category,
                "items": [
                    {
                        "name": name,
                        "price": int(price),
                        "available": True
                    }
                ]
            })

        save_data(data)
        await update_channel_message()
        await message.answer("Товар добавлен ✅")

    except Exception:
        await message.answer("Формат: /add категория | товар | цена")


@dp.message(Command("price"))
async def change_price(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    try:
        text = message.text.replace("/price", "", 1).strip()
        name, price = [x.strip() for x in text.split("|")]

        data = load_data()
        found = False

        for category in data:
            for item in category["items"]:
                if item["name"].lower() == name.lower():
                    item["price"] = int(price)
                    item["available"] = True
                    found = True

        save_data(data)
        await update_channel_message()

        await message.answer("Цена обновлена ✅" if found else "Товар не найден.")

    except Exception:
        await message.answer("Формат: /price товар | цена")


@dp.message(Command("off"))
async def off_item(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    name = message.text.replace("/off", "", 1).strip()
    data = load_data()
    found = False

    for category in data:
        for item in category["items"]:
            if item["name"].lower() == name.lower():
                item["available"] = False
                found = True

    save_data(data)
    await update_channel_message()

    await message.answer("Поставил ❌" if found else "Товар не найден.")


@dp.message(Command("on"))
async def on_item(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    name = message.text.replace("/on", "", 1).strip()
    data = load_data()
    found = False

    for category in data:
        for item in category["items"]:
            if item["name"].lower() == name.lower():
                item["available"] = True
                found = True

    save_data(data)
    await update_channel_message()

    await message.answer("Товар снова в наличии ✅" if found else "Товар не найден.")


@dp.message(Command("delete"))
async def delete_item(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    name = message.text.replace("/delete", "", 1).strip()
    data = load_data()
    found = False

    for category in data:
        before = len(category["items"])
        category["items"] = [
            item for item in category["items"]
            if item["name"].lower() != name.lower()
        ]

        if len(category["items"]) != before:
            found = True

    data = [cat for cat in data if cat["items"]]

    save_data(data)
    await update_channel_message()

    await message.answer("Товар удалён ✅" if found else "Товар не найден.")


@dp.message(Command("list"))
async def list_items(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    await message.answer(build_price_text())


@dp.message(Command("update"))
async def manual_update(message: Message):
    if not is_admin(message):
        return await message.answer("Нет доступа.")

    await update_channel_message()
    await message.answer("Прайс обновлён ✅")


async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(update_channel_message, "cron", hour=12, minute=0)
    scheduler.start()

    await update_channel_message()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
