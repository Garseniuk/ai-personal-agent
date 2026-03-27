# 🧠 Personal AI Assistant (Telegram Agent)

An autonomous AI agent built with Python and Telegram API, designed to help manage daily life by parsing natural language (text and voice) into structured data and providing insights through RAG (Retrieval-Augmented Generation).

## ✨ Features
* **Multimodal Processing:** Understands both text messages and voice notes (Speech-to-Text via Google Gemini API).
* **Agentic Intent Classification:** Uses Prompt Engineering to classify user input into actionable intents (expenses, tasks, queries).
* **Structured Data Extraction:** Forces the LLM to return strictly formatted JSON data.
* **Database Integration:** Automatically saves recognized expenses to a local SQLite database.
* **Retrieval-Augmented Generation (RAG):** Answers user queries about past expenses by fetching data from the database and using the LLM to summarize and analyze it.
* **Production Ready:** Fully containerized with Docker.

## 🛠️ Tech Stack
* **Language:** Python 3.11
* **Framework:** `aiogram` (Asynchronous Telegram Bot API)
* **AI Model:** Google Gemini 2.5 Flash (Multimodal capabilities)
* **Database:** SQLite3
* **Deployment:** Docker

## 🚀 How to run it locally

1. Clone the repository.
2. Create a `.env` file in the root directory and add your keys:
   ```text
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   GEMINI_API_KEY=your_gemini_api_key