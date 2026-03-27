import asyncio
import logging
import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
import google.generativeai as genai

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing environment variables. Check .env file.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

SYSTEM_PROMPT = """
Jesteś asystentem osobistym. Przeanalizuj wiadomość użytkownika (tekstową lub głosową) i sklasyfikuj ją do jednej z kategorii: "wydatek", "zadanie", "notatka".
Zwróć wynik TYLKO w formacie czystego JSON.
Struktura JSON:
{
  "kategoria": "wydatek/zadanie/notatka",
  "kwota": null (jeśli wydatek, podaj liczbę),
  "waluta": "PLN",
  "opis": "krótki opis",
  "czy_wymaga_akcji": true/false
}
"""

def init_db():
    """Initializes the SQLite database and creates the expenses table if it doesn't exist."""
    with sqlite3.connect('agent.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wydatki (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kwota REAL NOT NULL,
                waluta TEXT NOT NULL,
                opis TEXT,
                data_dodania TIMESTAMP
            )
        ''')
        conn.commit()

async def process_llm_response(response_text: str, message: types.Message, processing_msg: types.Message):
    """Parses LLM output, saves expenses to DB, and sends formatted reply."""
    try:
        raw_json = response_text.strip().removeprefix('```json').removesuffix('```').strip()
        parsed_data = json.loads(raw_json)
        
        reply_text = f"Zinterpretowane dane:\n```json\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}\n```\n"
        
        if parsed_data.get("kategoria") == "wydatek" and parsed_data.get("kwota") is not None:
            with sqlite3.connect('agent.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO wydatki (kwota, waluta, opis, data_dodania) VALUES (?, ?, ?, ?)",
                    (parsed_data["kwota"], parsed_data.get("waluta", "PLN"), parsed_data["opis"], datetime.now())
                )
                conn.commit()
            reply_text += "\n✅ Wydatek zapisany w bazie."

        await processing_msg.edit_text(reply_text, parse_mode="Markdown")
        
    except json.JSONDecodeError:
        logging.error(f"Failed to parse JSON from LLM: {response_text}")
        await processing_msg.edit_text("❌ Model zwrócił nieprawidłowy format danych.")
    except Exception as e:
        logging.error(f"Error processing response: {e}")
        await processing_msg.edit_text("❌ Wystąpił błąd podczas zapisywania danych.")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Agent gotowy. Wyślij tekst lub wiadomość głosową.")

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    processing_msg = await message.answer("Słucham...")
    local_filename = f"voice_{message.message_id}.ogg"
    
    try:
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, destination=local_filename)
        
        audio_file = genai.upload_file(path=local_filename)
        full_prompt = f"{SYSTEM_PROMPT}\n\nPrzeanalizuj dołączone nagranie głosowe."
        
        response = await model.generate_content_async([full_prompt, audio_file])
        await process_llm_response(response.text, message, processing_msg)
            
    except Exception as e:
        logging.error(f"Voice handling error: {e}")
        await processing_msg.edit_text("❌ Błąd przetwarzania głosu.")
    finally:
        # Zawsze sprzątamy pliki z dysku, nawet jak wystąpi błąd
        if os.path.exists(local_filename):
            os.remove(local_filename)

@dp.message(F.text)
async def handle_message(message: types.Message):
    processing_msg = await message.answer("Przetwarzam...")
    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nWiadomość: {message.text}"
        response = await model.generate_content_async(full_prompt)
        await process_llm_response(response.text, message, processing_msg)
    except Exception as e:
        logging.error(f"Text handling error: {e}")
        await processing_msg.edit_text("❌ Błąd przetwarzania tekstu.")

async def main():
    init_db()
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())