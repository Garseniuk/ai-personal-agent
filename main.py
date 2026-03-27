import asyncio
import logging
import os
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import google.generativeai as genai

# 1. Ładowanie bezpiecznych haseł z pliku .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Brak kluczy API! Sprawdź plik .env")

# 2. Konfiguracja logowania (profesjonalna praktyka)
logging.basicConfig(level=logging.INFO)

# 3. Inicjalizacja usług: Telegram Bot i Gemini API
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
genai.configure(api_key=GEMINI_API_KEY)

# Wybieramy lekki i bardzo szybki model, idealny do takich zadań
model = genai.GenerativeModel('gemini-2.5-flash')

# 4. PROMPT ENGINEERING (To pokażesz na rozmowie!)
# Zamiast gadać, AI ma wypluć surowe dane dla naszej przyszłej bazy SQL
SYSTEM_PROMPT = """
Jesteś asystentem osobistym. Przeanalizuj wiadomość użytkownika i sklasyfikuj ją do jednej z kategorii: "wydatek", "zadanie", "notatka".
Zwróć wynik TYLKO w formacie czystego JSON. Nie dodawaj żadnego powitania, wyjaśnień ani znaczników markdown (np. ```json).
Struktura JSON ma wyglądać dokładnie tak:
{
  "kategoria": "wydatek/zadanie/notatka",
  "kwota": null (jeśli to wydatek, podaj samą liczbę),
  "waluta": "PLN" (lub inna, jeśli podano),
  "opis": "krótki, rzeczowy opis",
  "czy_wymaga_akcji": true/false
}
"""

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Cześć! Dostałem przed chwilą mózg. Napisz mi coś w stylu: 'Wdałem dzisiaj 25 zł na kebaba' albo 'Przypomnij mi jutro o wizycie u dentysty'.")

@dp.message()
async def handle_message(message: types.Message):
    # Wysyłamy informację, że bot pracuje
    processing_msg = await message.answer("🧠 Analizuję Twoją wiadomość...")
    
    try:
        # Łączymy naszą instrukcję systemową z tym, co napisałeś na Telegramie
        full_prompt = f"{SYSTEM_PROMPT}\n\nWiadomość użytkownika: {message.text}"
        
        # Asynchroniczne wywołanie modelu (ważne przy apkach sieciowych!)
        response = await model.generate_content_async(full_prompt)
        
        # Oczyszczamy odpowiedź (czasem modele dodają znaczniki formatowania)
        raw_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
        
        # Próbujemy odczytać to jako kod JSON (weryfikacja czy AI się nie pomyliło)
        parsed_data = json.loads(raw_json)
        
        # Formatuje JSONa ładnie z wcięciami, żeby świetnie wyglądał na Telegramie
        formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
        
        # Edytujemy poprzednią wiadomość "Analizuję..." na gotowy wynik
        await processing_msg.edit_text(f"Oto ustrukturyzowane dane wyciągnięte z Twojego zdania:\n```json\n{formatted_json}\n```", parse_mode="Markdown")
        
    except json.JSONDecodeError:
        await processing_msg.edit_text("❌ Model AI zwrócił błędny format danych. Spróbuj napisać to inaczej.")
    except Exception as e:
        await processing_msg.edit_text(f"❌ Wystąpił błąd systemu: {e}")

async def main():
    logging.info("Uruchamianie Agenta AI...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())