from config import settings
from schemas import Chunk

def split_text(text: str) -> list[Chunk]:
    """
    Splits text into chunks of ~CHUNK_SIZE characters, trying to cut at 
    paragraph or sentence boundaries.
    """
    chunks = []
    cursor = 0
    text_len = len(text)
    index = 0

    while cursor < text_len:
        end = min(cursor + settings.CHUNK_SIZE, text_len)
        
        if end < text_len:
            # Look at the last 500 characters of this chunk
            search_start = max(cursor, end - 500)
            substring = text[search_start:end]
            
            last_paragraph = substring.rfind("\n\n")
            if last_paragraph != -1:
                end = search_start + last_paragraph + 2
            else:
                # b. If no paragraph break, look for a sentence end (.) in the last 200 chars
                search_start = max(cursor, end - 200)
                substring = text[search_start:end]
                last_period = substring.rfind(".")
                if last_period != -1:
                    end = search_start + last_period + 1

        # 2. Extract the chunk and save it
        chunk_text = text[cursor:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                index=index,
                start=cursor,
                end=end,
                text=chunk_text
            ))
            index += 1

        # 3. Check if we hit the max chunks limit
        if len(chunks) > settings.MAX_CHUNKS:
            raise ValueError("text_too_long")

        if end == text_len:
            break
            
        cursor = end - settings.OVERLAP

    return chunks