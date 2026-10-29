import httpx
import json
from config import settings
from schemas import CardList
from prompts import build_prompt

async def generate_cards_from_chunk(text: str) -> CardList:
    """
    Sends a text chunk to Ollama and returns structured cards.
    Includes a retry mechanism if the AI returns invalid JSON.
    """
    prompt = build_prompt(text)
    
    card_schema = CardList.model_json_schema()
    
    # 2. Construct the payload for Ollama
    payload = {
        "model": settings.MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "format": card_schema, # THE MAGIC CAGE
        "stream": False,
        "options": {
            "temperature": 0,
            "num_ctx": 4096
        }
    }

    url = f"{settings.OLLAMA_BASE_URL}/api/chat"

    # 3. Retry Loop (Attempt 1, Attempt 2)
    for attempt in range(2):
        try:
            # We use a 120-second timeout because local LLMs can take a while
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                ai_text = data["message"]["content"]
                
                # 4. Validate and parse the AI's response
                parsed_cards = CardList.model_validate_json(ai_text)
                return parsed_cards
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # If Ollama is off or taking too long, don't retry (it will just fail again)
            if attempt == 1:
                raise RuntimeError("llm_timeout") from e
            
        except Exception as e:
            if attempt == 1:
                raise RuntimeError("llm_invalid") from e
            
    # This should theoretically never be reached, but just in case
    raise RuntimeError("llm_failed")