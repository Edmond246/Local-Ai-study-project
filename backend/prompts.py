from config import settings

PROMPT_TEMPLATE = """You are a study assistant. Extract the key facts from the text
below and turn them into flashcards.

Rules:
- Each card tests ONE fact.
- Questions must be answerable from the text alone.
- Answers should be concise (1-2 sentences).
- Aim for {n} cards.
- Return ONLY valid JSON: {{"cards": [{{"question": "...", "answer": "..."}}]}}

TEXT:
{text}
"""

def target_cards(text: str) -> int:
    """
    Calculates how many cards the AI should aim to generate for a given chunk of text.
    Formula: len(text) // 400, clamped between CARD_TARGET_MIN and CARD_TARGET_MAX.
    """
    # 1 card per 400 chars
    calculated_n = len(text) // 400
    
    # keep it between 3 and 15
    n = max(settings.CARD_TARGET_MIN, min(calculated_n, settings.CARD_TARGET_MAX))
    
    return n

def build_prompt(text: str) -> str:
    """
    Generates the final prompt to send to the LLM.
    """
    n = target_cards(text)
    return PROMPT_TEMPLATE.format(n=n, text=text)