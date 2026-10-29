from pydantic import BaseModel, Field

class Card(BaseModel):
    question: str
    answer: str

class CardList(BaseModel):
    cards: list[Card]

class GenerateRequest(BaseModel):
    text: str

class GeneratedCard(Card):
    id: str
    chunk_index: int

class GenerateResponse(BaseModel):
    cards: list[GeneratedCard]
    warnings: list[str] = []

class RegenerateRequest(BaseModel):
    chunk_index: int
    question: str

class RegenerateResponse(BaseModel):
    card: GeneratedCard

class JobStatus(BaseModel):
    done: int
    total: int

class Chunk(BaseModel):
    index: int
    start: int
    end: int
    text: str