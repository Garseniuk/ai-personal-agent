import asyncio
import logging
import os
import json
import sqlite3 # NOWOŚĆ: Wbudowana biblioteka baz danych
from datetime import datetime # NOWOŚĆ: Do zapisywania czasu
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import google.generativeai as genai

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Brak kluczy API! Sprawdź plik .env")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

SYSTEM_PROMPT = """
Jesteś asystentem osobistym. Przeanalizuj wiadomość użytkownika i sklasyfikuj ją do jednej z kategorii: "wydatek", "zadanie", "notatka".
Zwróć wynik TYLKO w formacie czystego JSON. Nie dodawaj żadnego powitania.
Struktura JSON ma wyglądać dokładnie tak:
{
  "kategoria": "wydatek/zadanie/notatka",
  "kwota": null (jeśli to wydatek, podaj samą liczbę),
  "waluta": "PLN",
  "opis": "krótki, rzeczowy opis",
  "czy_wymaga_akcji": true/false
}
"""

# NOWOŚĆ: Funkcja inicjalizująca bazę danych SQL
def init_db():
    conn = sqlite3.connect('agent.db') # Tworzy plik agent.db
    cursor = conn.cursor()
    # Piszemy czysty SQL - to pokażesz na rozmowie!
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
    conn.close()
    logging.info("Baza danych gotowa.")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Cześć! Dostałem przed chwilą mózg i bazę danych. Napisz mi o jakimś wydatku!")

@dp.message()
async def handle_message(message: types.Message):
    processing_msg = await message.answer("🧠 Przetwarzam...")
    
    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nWiadomość użytkownika: {message.text}"
        response = await model.generate_content_async(full_prompt)
        
        raw_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
        parsed_data = json.loads(raw_json)
        
        reply_text = f"Oto zinterpretowane dane:\n```json\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}\n```\n"
        
        # NOWOŚĆ: Zapis do bazy danych, jeśli to wydatek
        if parsed_data.get("kategoria") == "wydatek" and parsed_data.get("kwota") is not None:
            conn = sqlite3.connect('agent.db')
            cursor = conn.cursor()
            
            # Parametryzowane zapytanie SQL (chroni przed SQL Injection - bardzo ważna praktyka!)
            cursor.execute(
                "INSERT INTO wydatki (kwota, waluta, opis, data_dodania) VALUES (?, ?, ?, ?)",
                (parsed_data["kwota"], parsed_data.get("waluta", "PLN"), parsed_data["opis"], datetime.now())
            )
            conn.commit()
            conn.close()
            
            reply_text += "\n✅ **Zapisano wydatek bezpiecznie w bazie SQL!**"

        await processing_msg.edit_text(reply_text, parse_mode="Markdown")
        
    except json.JSONDecodeError:
        await processing_msg.edit_text("❌ Model AI zwrócił błędny format danych.")
    except Exception as e:
        await processing_msg.edit_text(f"❌ Wystąpił błąd: {e}")

async def main():
    init_db() # Odpalamy bazę przed startem bota
    logging.info("Uruchamianie Agenta AI...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())