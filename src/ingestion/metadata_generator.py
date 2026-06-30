from dataclasses import dataclass
import json
import re
from src.llm.client import LLMClient

@dataclass
class ChunkMetadata:
    source_document: str
    collection: str
    content_type: str
    language: str
    topic: str
    keywords: list[str]
    contains_dosage: bool
    contains_recommendation: bool

# Regex patterns (ported from v1 and extended for Hindi)
DOSAGE_PATTERN = re.compile(
    r'\b\d+(?:\.\d+)?\s*(?:mg|mmol/L|mU|units?|g/kg|IU|mL|%|mg/dL|mcg|µg|g)\b',
    re.IGNORECASE
)

# Recommendation keywords (English and common transliterations/terms)
RECOMMENDATION_KEYWORDS = re.compile(
    r'\b(should|must|recommend|protocol|administer|initiate|advised?|indicated|prescri|titrat|start with|give|consider|use|avoid|monitor|check|measure|chahiye|karein|karna)\b',
    re.IGNORECASE
)

METADATA_PROMPT = """
You are a medical metadata classifier for a type 1 diabetes RAG system.
Return ONLY valid JSON with keys "topic" and "keywords".

STRICT RULES:
1. "topic" must be exactly one of the following topics:
   screening, diagnosis, monitoring, insulin_therapy, hypoglycemia, hyperglycemia, DKA, complications, epidemiology, nutrition, exercise, technology, psychosocial, sick_day_management, surgery, travel, pregnancy, general
2. "keywords" must be a list of 2-5 key medical terms found in the text.
3. Return ONLY valid JSON (no markdown block, no explanation).

TEXT:
{input_text}
"""

def safe_json_loads(text: str) -> dict:
    """Robustly parse JSON output from LLM, stripping markdown fencing if present."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        text = text.strip("` \n")
        
        try:
            return json.loads(text)
        except Exception as e:
            raise ValueError(f"Failed to parse LLM JSON response: {e}. Raw: {text}")

class MetadataGenerator:
    def __init__(self, llm_client: LLMClient, model: str):
        self.llm = llm_client
        self.model = model

    def generate(
        self,
        chunk_text: str,
        source_doc: str,
        collection: str,
        content_type: str,
        language: str
    ) -> ChunkMetadata:
        """Generates metadata for a chunk using LLM classification + regex rules."""
        
        # 1. Run local regex checks
        contains_dosage = bool(DOSAGE_PATTERN.search(chunk_text))
        contains_recommendation = bool(RECOMMENDATION_KEYWORDS.search(chunk_text))
        
        # 2. Query LLM for topic and keywords
        prompt = METADATA_PROMPT.format(input_text=chunk_text)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            raw_response = self.llm.chat(messages, model=self.model, temperature=0.1, max_tokens=150)
            parsed = safe_json_loads(raw_response)
            topic = parsed.get("topic", "general").strip().lower()
            keywords = parsed.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = [str(keywords)]
        except Exception as e:
            print(f"[WARN] LLM metadata generation failed, using fallbacks: {e}")
            topic = "general"
            keywords = []
            
        # Validate topic against allowed topics list
        allowed_topics = {
            "screening", "diagnosis", "monitoring", "insulin_therapy",
            "hypoglycemia", "hyperglycemia", "dka", "complications",
            "epidemiology", "nutrition", "exercise", "technology",
            "psychosocial", "sick_day_management", "surgery", "travel",
            "pregnancy", "general"
        }
        if topic not in allowed_topics:
            topic = "general"
            
        return ChunkMetadata(
            source_document=source_doc,
            collection=collection,
            content_type=content_type,
            language=language,
            topic=topic,
            keywords=keywords,
            contains_dosage=contains_dosage,
            contains_recommendation=contains_recommendation
        )
