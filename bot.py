import asyncio
import json
import os
from collections import defaultdict

import gspread
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from google.oauth2.service_account import Credentials


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SHEET_URL = os.getenv("SHEET_URL")
GOOGLE_JSON = os.getenv("GOOGLE_JSON")

MESSAGE_FILE = "message.json"


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)


def get_sheet_rows():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_JSON),
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1
    return sheet.get_all_records()


def format_price(value):
    if value is None or value == "":
        return "❌"

    try:
        value = int(str(value).replace(" ", "").replace(".", "").replace(",", ""))
        return f"{value:,}".replace(",", ".") + "₽"
    except Exception:
        return str(value)


def build_message(rows):
    grouped = defaultdict(list)

    for row in rows:
        category = row.get("category", "").strip()
        if not category:
            continue
        grouped[category].append(row)

    parts = []

    for category, items in grouped.items():
        parts.append(f"<b>{category}</b>\n")

        for row in items:
            title = str(row.get("title", "")).strip()
            color = str(row.get("color", "")).strip()
            available = str(row.get("available", "yes")).lower().strip()
            price_raw = row.get("price", "")

            price = "❌" if available in ["no", "нет", "0", "false"] else format_price(price_raw)

            line = f"📱<code>{title} {color} — {price}</code>"
            parts.append(line)

        parts.append("\n━━━━━━━━━━━━━━\n")

    parts.append(
        "eSIM - только виртуальные (нет физического слота под сим)\n\n"
        "SIM+eSIM - одна физическая сим карта + виртуальные\n\n"
        "🛒 Для заказа:\n"
        "@netizenstaff"
    )

    return "\n".join(parts)


def load_message_id():
    try:
        with open(MESSAGE_FILE, "r", encoding="utf-8") as file:
            return json.load(file).get("message_id")
    except Exception:
        return None


def save_message_id(message_id):
    with open(MESSAGE_FILE, "w", encoding="utf-8") as file:
        json.dump({"message_id": message_id}, file)


async def update_price_message():
    rows = get_sheet_rows()
    text = build_message(rows)
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

        print("Price message updated")

    except Exception as e:
        print("Error:", e)
        msg = await bot.send_message(CHANNEL_ID, text)
        save_message_id(msg.message_id)


async def main():
    await update_price_message()

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(update_price_message, "cron", hour=12, minute=0)
    scheduler.start()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
