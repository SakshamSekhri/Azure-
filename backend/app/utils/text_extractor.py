import hashlib
import io
from pathlib import Path
from typing import Tuple
import pypdf
import docx
from fastapi import UploadFile, HTTPException


def compute_file_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of raw file bytes for deduplication and caching."""
    return hashlib.sha256(file_bytes).hexdigest()


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from PDF, DOCX, or TXT file bytes."""
    ext = Path(filename).suffix.lower()
    text = ""

    try:
        if ext == ".pdf":
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            extracted_pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
            text = "\n".join(extracted_pages)

        elif ext in [".docx", ".doc"]:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        elif ext in [".txt", ".md"]:
            text = file_bytes.decode("utf-8", errors="replace")

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{ext}'. Allowed formats: .pdf, .docx, .txt"
            )

        cleaned_text = text.strip()
        if not cleaned_text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from file or file is empty."
            )
        return cleaned_text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process {filename}: {str(e)}"
        )
