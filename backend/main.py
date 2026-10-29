from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
import io
import uuid
import asyncio
import difflib

from config import settings
from schemas import (
    GenerateRequest, GenerateResponse, GeneratedCard, 
    RegenerateRequest, RegenerateResponse, JobStatus
)
from chunker import split_text
from llm import generate_cards_from_chunk
from extractors import extract_text_from_file
from exporters import export_to_csv, export_to_anki

# --- In-Memory Storage ---
JOBS = {}           # Stores progress: { "job_id": { "done": 0, "total": 5 } }
JOB_RESULTS = {}    # Stores cards when finished
CHUNK_CACHE = {}    # Stores chunks for regenerate: { "job_id": [Chunk(...), ...] }

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup self-check (from plan §4)
    print(f"✅ Server starting. Using model: {settings.MODEL_NAME}")
    print(f"✅ Expecting Ollama at: {settings.OLLAMA_BASE_URL}")
    yield
    print("🛑 Server shutting down.")

app = FastAPI(lifespan=lifespan)

# ==========================================
# 1. GENERATE (Background Job)
# ==========================================
async def process_generation(job_id: str, text: str):
    try:
        # 1. Split text
        try:
            chunks = split_text(text)
        except ValueError:
            JOBS[job_id]["error"] = "text_too_long"
            return

        JOBS[job_id]["total"] = len(chunks)
        CHUNK_CACHE[job_id] = chunks
        
        all_cards = []
        warnings = []

        # 2. Process each chunk
        for chunk in chunks:
            try:
                # Call Ollama
                card_list = await generate_cards_from_chunk(chunk.text)
                
                # Convert to GeneratedCard and attach IDs
                for c in card_list.cards:
                    all_cards.append(GeneratedCard(
                        id=f"c{uuid.uuid4().hex[:6]}",
                        question=c.question,
                        answer=c.answer,
                        chunk_index=chunk.index
                    ))
            except RuntimeError as e:
                warnings.append(f"Chunk {chunk.index} failed: {str(e)}")
            
            # Update progress
            JOBS[job_id]["done"] += 1

        # 3. Fuzzy Deduplication (from plan §3)
        unique_cards = []
        for card in all_cards:
            is_duplicate = False
            for existing in unique_cards:
                # Compare lowercase questions using similarity ratio
                ratio = difflib.SequenceMatcher(
                    None, card.question.lower(), existing.question.lower()
                ).ratio()
                if ratio > 0.85: # 85% similar = duplicate
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_cards.append(card)
        
        if len(all_cards) != len(unique_cards):
            warnings.append(f"Removed {len(all_cards) - len(unique_cards)} duplicate cards.")

        # 4. Save results
        JOB_RESULTS[job_id] = {
            "cards": unique_cards,
            "warnings": warnings
        }

    except Exception as e:
        JOBS[job_id]["error"] = "internal_error"

@app.post("/api/generate")
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    if not request.text.strip():
        raise HTTPException(status_code=422, detail={"error": "bad_input", "detail": "Text is empty"})

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"done": 0, "total": 0}
    
    # Start the background task so the frontend doesn't freeze
    background_tasks.add_task(process_generation, job_id, request.text)
    
    return {"job_id": job_id}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    status = JOBS[job_id]
    
    # If an error occurred during chunking
    if status.get("error") == "text_too_long":
        max_chars = settings.MAX_CHUNKS * settings.CHUNK_SIZE // 1000
        raise HTTPException(
            status_code=413, 
            detail={"error": "text_too_long", "detail": f"Text too long — {settings.MAX_CHUNKS} chunks max (~{max_chars}k chars). Split your notes."}
        )

    # If finished, return the cards
    if status["total"] > 0 and status["done"] == status["total"]:
        result = JOB_RESULTS.get(job_id, {"cards": [], "warnings": []})
        return {
            "status": "done",
            "done": status["done"],
            "total": status["total"],
            "cards": result["cards"],
            "warnings": result["warnings"]
        }
        
    # Otherwise, still processing
    return {"status": "processing", "done": status["done"], "total": status["total"]}

# ==========================================
# 2. REGENERATE
# ==========================================
@app.post("/api/regenerate")
async def regenerate(request: RegenerateRequest):

    # mock this by finding the chunk in the most recent job.
    latest_job = list(CHUNK_CACHE.keys())[-1] if CHUNK_CACHE else None
    
    if not latest_job:
        raise HTTPException(status_code=404, detail="No active job found to regenerate from.")
        
    chunks = CHUNK_CACHE[latest_job]
    # Find the specific chunk
    target_chunk = next((c for c in chunks if c.index == request.chunk_index), None)
    
    if not target_chunk:
        raise HTTPException(status_code=404, detail="Chunk not found.")
        
    try:
        # Ask LLM for a new card
        card_list = await generate_cards_from_chunk(target_chunk.text)
        new_card = card_list.cards[0] # Grab the first one
        
        return RegenerateResponse(card=GeneratedCard(
            id=f"c{uuid.uuid4().hex[:6]}",
            question=new_card.question,
            answer=new_card.answer,
            chunk_index=request.chunk_index
        ))
    except Exception:
        raise HTTPException(status_code=502, detail={"error": "llm_invalid", "detail": "Could not regenerate."})

# ==========================================
# 3. FILE UPLOAD & EXPORT
# ==========================================
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # 1 MB limit check
    content = await file.read()
    if len(content) > 1024 * 1024:
        raise HTTPException(status_code=413, detail={"error": "text_too_long", "detail": "File exceeds 1MB"})
    
    # Reset file pointer for extractors
    await file.seek(0)
    text = await extract_text_from_file(file)
    return {"text": text}

@app.post("/api/export/csv")
async def export_csv(cards: list[GeneratedCard]):
    csv_data = export_to_csv(cards)
    return Response(
        content=csv_data, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=flashcards.csv"}
    )

@app.post("/api/export/anki")
async def export_anki(cards: list[GeneratedCard]):
    apkg_bytes = export_to_anki(cards)
    return Response(
        content=apkg_bytes, 
        media_type="application/octet-stream", 
        headers={"Content-Disposition": "attachment; filename=flashcards.apkg"}
    )

# ==========================================
# 4. STATIC FRONTEND MOUNT (Must be at the bottom)
# ==========================================
import os
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")