import json
from typing import List, Dict
import os
from dotenv import load_dotenv
from pathlib import Path

# Attempt to import the GenAI client from known provider packages.
# Different environments may expose this as `from google import genai` or
# `import google.generativeai as genai`. Fall back gracefully and
# provide informative errors if unavailable.
try:
    from google import genai  # preferred in some installs
except Exception:
    try:
        import google.genai as genai
    except Exception:
        genai = None

# -------------------------------
# CONFIG (SET YOUR API KEY)
# -------------------------------
load_dotenv()
# Initialize a client abstraction depending on the imported library.
if genai is None:
    client = None
else:
    # Some genai packages expose a Client class, others expose top-level functions.
    if hasattr(genai, "Client"):
        client = genai.Client(api_key=os.getenv("llm_key"))
    else:
        # e.g. google.generativeai often uses a configure() + generate() pattern
        if hasattr(genai, "configure"):
            try:
                genai.configure(api_key=os.getenv("llm_key"))
            except Exception:
                pass
        client = genai


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
    if client is None:
        raise ImportError(
            "GenAI client not available. Install 'google-generativeai' or the appropriate SDK "
            "and set the environment variable 'llm_key'."
        )

    # Try different client interfaces depending on the installed package.
    try:
        # Newer SDKs may provide a `Client` with `models.generate_content`
        if hasattr(client, "models") and hasattr(client.models, "generate_content"):
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
            text = getattr(response, "text", None)
            if text is None:
                # some responses return dict-like objects
                try:
                    text = response.get("candidates", [])[0].get("content", "")
                except Exception:
                    text = str(response)

        # Older google.generativeai exposes a top-level `generate` function
        elif hasattr(genai, "generate"):
            response = genai.generate(model="gemini-2.5-flash-lite", input=prompt)
            text = getattr(response, "text", None) or response.get("candidates", [])[0].get("content", "")

        else:
            # Fallback: try calling a `generate` method on the client object
            if hasattr(client, "generate"):
                response = client.generate(model="gemini-2.5-flash-lite", input=prompt)
                text = getattr(response, "text", None) or str(response)
            else:
                raise RuntimeError("Unsupported GenAI client API; please update the SDK or adapt this wrapper.")

    except Exception as e:
        raise

    return text.strip()


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

# -------------------------------
# L3 EXTRACTION PROMPT
# -------------------------------

L3_EXTRACTION_PROMPT = """
You are extracting atomic clinical facts from a medical guideline.

STRICT RULES:
1. Extract ONLY facts that must be preserved EXACTLY
2. DO NOT paraphrase
3. Keep each fact self-contained
4. Include numbers, units, thresholds EXACTLY
5. Split multi-step instructions into separate items
6. IGNORE explanations, background, or descriptive text
7. If a sentence contains multiple actions or conditions, split into separate items
8. NEVER return headings, labels, or section titles
9. Each item MUST be a complete sentence

Return ONLY valid JSON:

[
    {{
        "text": "..."
    }}
]

TEXT:
{input_text}
"""


# -------------------------------
# L3 GENERATION FOR SINGLE L2
# -------------------------------

def generate_l3_from_l2(l2_chunk: Dict) -> List[Dict]:
    """
    Generate L3 chunks (atomic facts) from a single L2 chunk.
    """

    prompt = L3_EXTRACTION_PROMPT.format(input_text=l2_chunk["text"])

    raw_output = call_gemini(prompt)

    try:
        l3_items = safe_json_loads(raw_output)
    except Exception as e:
        print("[ERROR] L3 parsing failed")
        print(raw_output)
        raise e

    l3_chunks = []

    for idx, item in enumerate(l3_items):
        text = item.get("text", "").strip()

        # Basic filtering (IMPORTANT)
        if not text:
            continue
        
        # Reject headers / labels
        if text.isupper():
            continue

        if len(text.split()) < 5:
            continue

        if text.endswith(":"):
            continue

        # Reject fragments (no verb heuristic)
        if not any(v in text.lower() for v in ["is", "are", "was", "were", "has", "have", "should", "results", "leads"]):
            continue

        if len(text.split()) < 3:
            continue  # too small, likely noise

        l3_chunks.append({
            "chunk_id": f"{l2_chunk['chunk_id']}_L3_{idx+1}",
            "parent_id": l2_chunk["chunk_id"],
            "level": 3,
            "text": text
        })

    return l3_chunks


# -------------------------------
# L3 GENERATION FOR FILE (TEST MODE)
# -------------------------------

def generate_l3_for_file(
    l2_chunks: List[Dict],
    output_path: str = "temp_l3.json",
    checkpoint_path: str | Path | None = None,
) -> List[Dict]:
    """
    Generate L3 chunks for a single file's L2 chunks.
    Saves output to project root as temp_l3.json
    """

    checkpoint_path = Path(checkpoint_path) if checkpoint_path else Path(str(output_path) + ".checkpoint.json")
    all_l3_chunks: List[Dict] = []
    working_l2_chunks: List[Dict] = l2_chunks
    start_idx = 0

    if checkpoint_path.exists():
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        working_l2_chunks = state.get("l2_chunks", l2_chunks)
        all_l3_chunks = state.get("l3_chunks", [])
        last_completed_index = state.get("last_completed_index", -1)
        start_idx = max(0, last_completed_index + 1)
        print(
            f"[RESUME-L3] Loaded checkpoint {checkpoint_path} | "
            f"last completed L2 index: {last_completed_index}"
        )

    for i in range(start_idx, len(working_l2_chunks)):
        l2 = working_l2_chunks[i]
        print(f"[L3] Processing {i+1}/{len(working_l2_chunks)}: {l2['chunk_id']}")

        try:
            l3_chunks = generate_l3_from_l2(l2)

            # Attach child_ids to L2
            l2["child_ids"] = [c["chunk_id"] for c in l3_chunks]
            all_l3_chunks.extend(l3_chunks)

        except Exception as e:
            print(f"[ERROR] Failed on {l2['chunk_id']}: {e}")
            l2["child_ids"] = []

        finally:
            checkpoint_payload = {
                "last_completed_index": i,
                "l2_chunks": working_l2_chunks,
                "l3_chunks": all_l3_chunks,
            }
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_payload, f, indent=2, ensure_ascii=False)

    # Save final output
    output_data = {
        "l2_chunks": working_l2_chunks,
        "l3_chunks": all_l3_chunks
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    if checkpoint_path.exists():
        checkpoint_path.unlink()

    print(f"[DONE] L3 saved to {output_path}")

    return all_l3_chunks