🧠 Local AI Study Tool

A fully local, privacy-first AI flashcard generator. Just drop in some text or upload a PDF, and a local 3B model (Qwen 2.5) will pull out the key facts and whip up a solid set of Q&A flashcards for you. Export them straight to CSV or Anki—no cloud APIs, and zero data leaving your machine.

What it does

100% Local: Powered by Ollama.

Smart Chunking: Automatically breaks down long texts at natural sentence and paragraph boundaries so the AI doesn't lose context.
Structured Output: Uses Pydantic JSON schemas to make sure the AI actually returns clean, usable data instead of rambling.
Fuzzy Deduplication: Cleans up duplicate flashcards across different chunks so your deck stays clean.
Background Jobs: Built-in progress tracking so you can see how long a heavy PDF takes to process.
Easy Exports: Download your decks directly as .csv or Anki .apkg files.

Tech Stack

Backend: Python, FastAPI, Pydantic, httpx
Frontend: Vanilla HTML/CSS/JS (served right out of FastAPI)
AI: Ollama running Qwen 2.5 (3B)

🚀 How to run it

Prerequisites
Make sure you have these installed:

Ollama up and running locally.
Python 3.10+.

Clone the repository and pull the AI model to get started:

git clone https://github.com/YOUR_USERNAME/local-ai-study-tool.git
cd local-ai-study-tool
ollama pull qwen2.5:3b

2. Set up the Backend
Navigate to the backend folder and set up your Python environment:

cd backend
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

3. Configure Environment Variables
Copy the example config to create your local .env file:

bash
cp .env.example .env

4. Start the App
bash
uvicorn main:app --reload