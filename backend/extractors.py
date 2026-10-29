import io
from pypdf import PdfReader
from fastapi import UploadFile, HTTPException

async def extract_text_from_file(file: UploadFile) -> str:
    """
    Takes an uploaded file (txt or pdf) and returns the plain text.
    """
    filename = file.filename.lower()
    
    # 1. Handle .txt files
    if filename.endswith(".txt"):
        content = await file.read()
        try:
            # Try to decode as UTF-8 text
            return content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=422, 
                detail="bad_input: Text file must be UTF-8 encoded."
            )

    # 2. Handle .pdf files
    elif filename.endswith(".pdf"):
        content = await file.read()
        try:
            # pypdf needs a file-like object, so we wrap the bytes in io.BytesIO
            pdf_reader = PdfReader(io.BytesIO(content))
            text = ""
            
            # Loop through every page and extract the text
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n" # Add double line break between pages
                    
            return text
        except Exception as e:
            raise HTTPException(
                status_code=422, 
                detail="bad_input: Could not read PDF file. It might be corrupted."
            )

    else:
        raise HTTPException(
            status_code=422, 
            detail="bad_input: Only .txt and .pdf files are supported."
        )