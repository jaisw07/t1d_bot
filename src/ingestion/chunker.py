import json
from typing import List, Dict
from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path

# -------------------------------
# CONFIG (SET YOUR API KEY)
# -------------------------------
load_dotenv()
client = genai.Client(api_key=os.getenv("llm_key"))


# -------------------------------
# PROMPT (STRICT - FROM SPEC)
# -------------------------------

CHUNKING_PROMPT = """
You are segmenting clinical guideline text into semantic units for a medical RAG system.

STRICT RULES:
1. Each chunk must be semantically complete (standalone meaning)
2. DO NOT split:
   - dosage instructions
   - numbered protocols
   - tables
3. Keep chunks between 200–400 tokens
4. Preserve exact wording (no paraphrasing)
5. Maintain clinical accuracy

Return ONLY valid JSON:

[
  {{
    "chunk_id": "chunk_1",
    "text": "..."
  }}
]

TEXT:
{input_text}
"""
# -------------------------------
# CHAPTERS TO BE SKIPPED
# -------------------------------
SKIP_TITLES = {
    "REFERENCES",
    "CONFLICT OF INTEREST",
    "ORCID",
    "ACKNOWLEDGMENTS",
    "AUTHOR CONTRIBUTIONS",
    "DATA AVAILABILITY STATEMENT",
    "PEER REVIEW"
}

SKIP_SUBSTRINGS = [
    "ISPAD CLINICAL PRACTICE CONSENSUS GUIDELINES 2022",
    "I S P A D G U I D E L I N E S"
]

# -------------------------------
# GEMINI CALL
# -------------------------------

def call_gemini(prompt: str) -> str:
    """
    Gemini LLM call (deterministic).
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
        config={
            "temperature": 0,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 8192
        }
    )

    return response.text.strip()


# -------------------------------
# JSON PARSER (ROBUST)
# -------------------------------

def safe_json_loads(text: str):
    """
    Handles cases where Gemini wraps JSON in ```json blocks.
    """
    try:
        return json.loads(text)
    except:
        # محاولة تنظيف
        text = text.strip()

        # remove markdown fencing
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]

        text = text.strip("` \n")

        # detect truncation
        if not text.endswith("]"):
            raise ValueError("LLM output likely truncated")

        return json.loads(text)
    
# -------------------------------
# CLEAN TEXT
# -------------------------------    
def clean_text(text: str) -> str:
    """
    Fix PDF extraction artifacts:
    - hyphenated line breaks
    - excessive newlines
    - broken words
    """

    import re

    # Fix hyphenated line breaks: "hypoglyce-\nmia" → "hypoglycemia"
    text = re.sub(r"-\n\s*", "", text)

    # Fix broken newlines inside sentences
    text = re.sub(r"\n(?=[a-z])", " ", text)

    # Replace multiple newlines with single
    text = re.sub(r"\n+", "\n", text)

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()

# -------------------------------
# MAIN CHUNKER
# -------------------------------

def chunk_chapter(chapter: Dict) -> List[Dict]:
    """Convert one chapter into semantic chunks."""

    full_text = "\n".join(chapter["content"])
    full_text = clean_text(full_text)

    prompt = CHUNKING_PROMPT.format(input_text=full_text)

    raw_output = call_gemini(prompt)

    try:
        chunks = safe_json_loads(raw_output)
    except Exception as e:
        print("[ERROR] Failed to parse Gemini output")
        print(raw_output)
        raise e

    return chunks


def chunk_document(chapters: List[Dict]) -> List[Dict]:
    """Chunk entire document."""

    all_chunks = []

    for i, chapter in enumerate(chapters):
        title = chapter["title"]
        title_upper = title.upper()

        # Skip exact titles
        if any(skip in title_upper for skip in SKIP_TITLES):
            print(f"[SKIP] Skipping chapter (title match): {title}")
            continue

        # Skip substring patterns (your ISPAD case)
        if any(substr in title_upper for substr in SKIP_SUBSTRINGS):
            print(f"[SKIP] Skipping chapter (substring match): {title}")
            continue

        print(f"[INFO] Chunking chapter {i+1}: {chapter['title']}")

        chunks = chunk_chapter(chapter)

        # Attach metadata (IMPORTANT for later steps)
        for idx, c in enumerate(chunks):
            c["chunk_id"] = f"{chapter['title']}_chunk_{idx+1}"
            c["chapter_title"] = chapter["title"]
            c["start_page"] = chapter["start_page"]
            c["level"] = 2

        all_chunks.extend(chunks)

    return all_chunks


def _save_checkpoint(checkpoint_path: Path, last_completed_index: int, chunks: List[Dict]) -> None:
    """Persist resumable progress for chapter-level chunking."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_completed_index": last_completed_index,
        "chunks": chunks,
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def chunk_document_resumable(chapters: List[Dict], checkpoint_path: str | Path) -> List[Dict]:
    """
    Chunk entire document and save progress after each chapter.
    If a run fails, rerunning resumes from the last completed chapter.
    """
    checkpoint_path = Path(checkpoint_path)
    all_chunks: List[Dict] = []
    start_idx = 0

    if checkpoint_path.exists():
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        all_chunks = state.get("chunks", [])
        last_completed_index = state.get("last_completed_index", -1)
        start_idx = max(0, last_completed_index + 1)
        print(
            f"[RESUME] Loaded checkpoint {checkpoint_path} | "
            f"last completed chapter index: {last_completed_index}"
        )

    for i in range(start_idx, len(chapters)):
        chapter = chapters[i]
        title = chapter["title"]
        title_upper = title.upper()

        if any(skip in title_upper for skip in SKIP_TITLES):
            print(f"[SKIP] Skipping chapter (title match): {title}")
            _save_checkpoint(checkpoint_path, i, all_chunks)
            continue

        if any(substr in title_upper for substr in SKIP_SUBSTRINGS):
            print(f"[SKIP] Skipping chapter (substring match): {title}")
            _save_checkpoint(checkpoint_path, i, all_chunks)
            continue

        print(f"[INFO] Chunking chapter {i+1}: {title}")

        chunks = chunk_chapter(chapter)

        for idx, c in enumerate(chunks):
            c["chunk_id"] = f"{title}_chunk_{idx+1}"
            c["chapter_title"] = title
            c["start_page"] = chapter["start_page"]
            c["level"] = 2

        all_chunks.extend(chunks)
        _save_checkpoint(checkpoint_path, i, all_chunks)

    return all_chunks