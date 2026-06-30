from dataclasses import dataclass
import json
import re
from src.llm.client import LLMClient
from .structure_detector import Section

from src.ingestion.metadata_generator import ChunkMetadata

@dataclass
class Chunk:
    chunk_id: str
    text: str
    section_title: str
    start_page: int
    end_page: int
    child_ids: list[str]
    metadata: ChunkMetadata | None = None

# Content-type-aware prompts
CHUNKING_PROMPTS = {
    "guideline": """
You are segmenting clinical guideline text into semantic units for a medical RAG system.

STRICT RULES:
1. Each chunk must be semantically complete (standalone meaning).
2. DO NOT split:
   - dosage instructions
   - clinical protocols/numbered recommendations
   - tables
3. Keep chunks between 200–400 tokens (or ~150-300 words).
4. Preserve exact wording (no paraphrasing).
5. Maintain clinical accuracy.

Return ONLY a valid JSON array of objects:
[
  {{
    "text": "..."
  }}
]

TEXT:
{input_text}
""",

    "textbook": """
You are segmenting textbook content into cohesive units for a medical RAG system.

STRICT RULES:
1. Each chunk must be explanatory and semantically complete.
2. Keep examples and case studies together with the concepts they explain.
3. Keep chunks between 250–500 tokens (or ~200-400 words).
4. Preserve exact wording (no paraphrasing).
5. Maintain technical and clinical accuracy.

Return ONLY a valid JSON array of objects:
[
  {{
    "text": "..."
  }}
]

TEXT:
{input_text}
""",

    "patient_education": """
You are segmenting patient education materials into simple, self-contained units for a RAG system.

STRICT RULES:
1. Each chunk must be simple, readable, and cover a single clear topic.
2. Keep instructions or action steps together.
3. Keep chunks between 150–300 tokens (or ~100-250 words).
4. Preserve exact wording (no paraphrasing).

Return ONLY a valid JSON array of objects:
[
  {{
    "text": "..."
  }}
]

TEXT:
{input_text}
"""
}

def clean_text(text: str) -> str:
    """Fix PDF extraction artifacts like hyphens, line breaks, spaces."""
    # Fix hyphenated line breaks: "hypoglyce-\nmia" → "hypoglycemia"
    text = re.sub(r"-\n\s*", "", text)
    # Fix broken newlines inside sentences
    text = re.sub(r"\n(?=[a-z])", " ", text)
    # Replace multiple newlines with single
    text = re.sub(r"\n+", "\n", text)
    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def safe_json_loads(text: str) -> list[dict]:
    """Robustly parse JSON output from LLM, stripping markdown fencing if present."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Remove markdown code blocks if any
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        text = text.strip("` \n")
        
        # Check for trailing characters or truncation
        if not text.endswith("]"):
            # Attempt to fix simple truncation by appending bracket
            if not text.endswith("}"):
                text += "}"
            text += "]"
            
        try:
            return json.loads(text)
        except Exception as e:
            raise ValueError(f"Failed to parse LLM JSON response: {e}. Raw: {text}")

class Chunker:
    def __init__(self, llm_client: LLMClient, model: str):
        self.llm = llm_client
        self.model = model

    def chunk(self, sections: list[Section], content_type: str) -> list[Chunk]:
        """Runs content-type-aware semantic chunking on sections."""
        prompt_template = CHUNKING_PROMPTS.get(content_type, CHUNKING_PROMPTS["guideline"])
        all_chunks = []

        for section in sections:
            full_text = "\n".join(section.content)
            cleaned = clean_text(full_text)
            if not cleaned:
                continue

            prompt = prompt_template.format(input_text=cleaned)
            messages = [{"role": "user", "content": prompt}]
            try:
                raw_response = self.llm.chat(messages, model=self.model, temperature=0.1)
                llm_chunks = safe_json_loads(raw_response)
            except Exception as e:
                print(f"[ERROR] Failed to chunk section '{section.title}': {e}")
                # Fallback: split section text into chunks of at most 1500 characters
                chunk_size = 1500
                overlap = 200
                llm_chunks = []
                start = 0
                while start < len(cleaned):
                    end = start + chunk_size
                    if end < len(cleaned):
                        last_space = cleaned.rfind(" ", end - 200, end)
                        if last_space != -1:
                            end = last_space
                    llm_chunks.append({"text": cleaned[start:end].strip()})
                    start = end - overlap if end - overlap > start else end
                if not llm_chunks:
                    llm_chunks = [{"text": cleaned}]
                
            for idx, c_data in enumerate(llm_chunks):
                text = c_data.get("text", "").strip()
                if not text:
                    continue
                    
                # Clean and truncate section title to prevent Milvus VARCHAR length errors
                safe_title = section.title.replace(' ', '_')
                safe_title = re.sub(r'[^a-zA-Z0-9_]', '', safe_title).strip('_')
                if not safe_title:
                    safe_title = "section"
                chunk_id = f"{safe_title[:80]}_chunk_{idx+1}"
                all_chunks.append(Chunk(
                    chunk_id=chunk_id,
                    text=text,
                    section_title=section.title,
                    start_page=section.start_page,
                    end_page=section.end_page,
                    child_ids=[]
                ))
                
        return all_chunks
