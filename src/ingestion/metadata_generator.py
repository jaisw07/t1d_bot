import json
import re
import logging
from pathlib import Path
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential

from src.ingestion.chunker import call_gemini

logger = logging.getLogger(__name__)


# -------------------------------
# PROMPT (USE YOUR CURRENT ONE)
# -------------------------------
METADATA_PROMPT = """
You are a medical metadata classifier for ISPAD clinical guideline chunks.
Your output is used for retrieval filtering — precision matters more than recall.

STRICT RULES:
1. Only use information present in the text. Do NOT infer beyond what is written.
2. When uncertain, choose the more conservative option.
3. Return ONLY valid JSON — no explanation, no markdown.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[severity]
- "emergency"  → immediate life-threatening condition (DKA, severe hypoglycemia, unconsciousness, shock)
- "urgent"     → needs same-day/prompt action (mild-moderate hypoglycemia, ketones present, high glucose)
- "routine"    → background, definitions, epidemiology, screening criteria, general recommendations

[contains_recommendation]
IMPORTANT: This is broader than step-by-step protocols.
- true  → text contains ANY of:
    • "should", "is recommended", "is advised", "is indicated"
    • numbered/bulleted action steps
    • explicit clinical decision rules ("if X, then Y")
    • dosage or treatment instructions
- false → purely descriptive, definitional, or epidemiological text

[contains_dosage]
- true  → text contains a numeric value with a clinical unit:
    mg, mmol/L, mU, units, g/kg, %, mg/dL, IU, mL
    Examples: "0.1 units/kg", "200 mg/dL", "1.5 mmol/L"
- false → otherwise

[audience]
- "clinician" → uses technical terms (HbA1c, OGTT, euglycemia, titration, bolus)
- "patient"   → plain language, avoids jargon, addresses "you" or "your child"
- "both"      → clearly addresses both (e.g., parent + provider sections)

[topic] — choose the SINGLE best match:
  "screening"       → identifying at-risk individuals before diagnosis (antibodies, genetic risk, family screening)
  "diagnosis"       → diagnostic criteria, thresholds, classification of diabetes type
  "monitoring"      → ongoing measurement (CGM, HbA1c targets, SMBG, frequency)
  "insulin_therapy" → insulin types, regimens, titration, delivery devices
  "hypoglycemia"    → low glucose events, treatment, prevention, awareness
  "hyperglycemia"   → high glucose, correction, sick-day rules (non-DKA)
  "DKA"             → diabetic ketoacidosis, ketones, acidosis management
  "complications"   → long-term complications (nephropathy, retinopathy, neuropathy, CVD)
  "epidemiology"    → incidence, prevalence, demographics, risk factors, natural history
  "general"         → does not fit any above (use sparingly)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEXT: "Islet autoantibodies (GADA, IA-2A, ZnT8A) should be measured in first-degree relatives 
of individuals with type 1 diabetes as part of family screening programs."
OUTPUT: {{"severity":"routine","contains_recommendation":true,"contains_dosage":false,"audience":"clinician","topic":"screening"}}

TEXT: "OGTT is recommended when fasting glucose is 5.6–6.9 mmol/L to confirm impaired glucose tolerance."
OUTPUT: {{"severity":"routine","contains_recommendation":true,"contains_dosage":true,"audience":"clinician","topic":"diagnosis"}}

TEXT: "For mild-to-moderate hypoglycemia, give 0.3 g/kg fast-acting carbohydrates (max 15g), 
then recheck glucose in 15 minutes."
OUTPUT: {{"severity":"urgent","contains_recommendation":true,"contains_dosage":true,"audience":"both","topic":"hypoglycemia"}}

TEXT: "The incidence of type 1 diabetes has increased approximately 3–4% per year in Europe over recent decades."
OUTPUT: {{"severity":"routine","contains_recommendation":false,"contains_dosage":false,"audience":"clinician","topic":"epidemiology"}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEXT TO CLASSIFY:
{input_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY this JSON (no extra keys):
{{
    "severity": "...",
    "contains_recommendation": true/false,
    "contains_dosage": true/false,
    "audience": "...",
    "topic": "..."
}}
"""


# -------------------------------
# REGEX RULES
# -------------------------------

DOSAGE_PATTERN = re.compile(
    r'\b\d+(?:\.\d+)?\s*(?:mg|mmol/L|mU|units?|g/kg|IU|mL|%|mg/dL|mcg|µg)\b',
    re.IGNORECASE
)

RECOMMENDATION_KEYWORDS = re.compile(
    r'\b(should|recommend|advised?|indicated|must|initiat|administer|prescri'
    r'|titrat|start with|give|consider|use|avoid|monitor|check|measure)\b',
    re.IGNORECASE
)

PROTOCOL_PATTERN = re.compile(
    r'(\b(step \d|first[,.]|then[,.]|if .{0,40}then|followed by)\b'
    r'|\n\s*\d+\.\s|\n\s*[-•]\s)',
    re.IGNORECASE
)


VALID_TOPICS = {
    "screening", "diagnosis", "monitoring", "insulin_therapy",
    "hypoglycemia", "hyperglycemia", "DKA", "complications",
    "epidemiology", "general"
}

VALID_SEVERITY = {"emergency", "urgent", "routine"}
VALID_AUDIENCE = {"clinician", "patient", "both"}


# -------------------------------
# RULE-BASED OVERRIDES (SAFE VERSION)
# -------------------------------

def rule_based_overrides(text: str, metadata: dict) -> dict:
    """
    Conservative overrides — avoids breaking semantics
    """

    # Dosage (reliable)
    metadata["contains_dosage"] = bool(DOSAGE_PATTERN.search(text))

    # Recommendation (balanced)
    llm_rec = metadata.get("contains_recommendation", False)
    rule_rec = bool(RECOMMENDATION_KEYWORDS.search(text)) or bool(PROTOCOL_PATTERN.search(text))

    # Slightly conservative (avoid long-text overfire)
    metadata["contains_recommendation"] = (
        llm_rec or (rule_rec and len(text) < 1200)
    )

    # ⚠️ IMPORTANT: NO AGGRESSIVE SEVERITY OVERRIDE
    # Only mild correction
    lower = text.lower()

    if any(w in lower for w in ["hypoglycemia", "hypoglycaemia", "low blood glucose"]):
        if metadata.get("severity") == "routine":
            metadata["severity"] = "urgent"

    return metadata


# -------------------------------
# VALIDATION
# -------------------------------

def validate_and_normalize(metadata: dict, text: str) -> dict:

    normalized = {
        "severity": metadata.get("severity", "routine"),
        "contains_recommendation": bool(metadata.get("contains_recommendation", False)),
        "contains_dosage": bool(metadata.get("contains_dosage", False)),
        "audience": metadata.get("audience", "clinician"),
        "topic": metadata.get("topic", "general"),
    }

    if normalized["severity"] not in VALID_SEVERITY:
        normalized["severity"] = "routine"

    if normalized["audience"] not in VALID_AUDIENCE:
        normalized["audience"] = "clinician"

    if normalized["topic"] not in VALID_TOPICS:
        normalized["topic"] = "general"

    # Apply overrides LAST
    normalized = rule_based_overrides(text, normalized)

    return normalized


# -------------------------------
# FALLBACK
# -------------------------------

def get_fallback_metadata(text: str) -> dict:
    return validate_and_normalize({
        "severity": "routine",
        "contains_recommendation": False,
        "contains_dosage": False,
        "audience": "clinician",
        "topic": "general",
    }, text)


# -------------------------------
# PARSER
# -------------------------------

def parse_llm_response(response_text: str, chunk_text: str) -> dict:
    try:
        clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_text.strip(), flags=re.MULTILINE)
        metadata = json.loads(clean)
        return validate_and_normalize(metadata, chunk_text)
    except Exception:
        return get_fallback_metadata(chunk_text)


# -------------------------------
# RETRY WRAPPER
# -------------------------------

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
def call_llm_with_retry(prompt: str) -> str:
    return call_gemini(prompt)


def _save_checkpoint(checkpoint_path: Path, last_completed_index: int, chunks: List[Dict]) -> None:
    """Persist resumable progress for metadata generation."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_completed_index": last_completed_index,
        "chunks": chunks,
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


# -------------------------------
# MAIN TAGGING FUNCTION
# -------------------------------

def tag_chunk(chunk: dict) -> dict:
    text = chunk["text"]

    try:
        raw_response = call_llm_with_retry(METADATA_PROMPT.format(input_text=text))
        metadata = parse_llm_response(raw_response, text)
        metadata["_meta_source"] = "llm"

    except Exception as e:
        logger.warning(f"LLM failed for chunk {chunk['chunk_id']}: {e}")
        metadata = get_fallback_metadata(text)
        metadata["_meta_source"] = "fallback"

    # Light review flag (not too aggressive)
    if metadata["topic"] == "general" and not metadata["contains_recommendation"]:
        metadata["_needs_review"] = True

    chunk["metadata"] = metadata
    return chunk


# -------------------------------
# FILE LEVEL
# -------------------------------

def generate_metadata_for_file(
    l2_chunks: List[Dict],
    output_path: str,
    checkpoint_path: str | Path | None = None,
) -> List[Dict]:

    checkpoint_path = Path(checkpoint_path) if checkpoint_path else Path(str(output_path) + ".checkpoint.json")

    updated_chunks: List[Dict] = []
    start_idx = 0

    if checkpoint_path.exists():
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        updated_chunks = state.get("chunks", [])
        last_completed_index = state.get("last_completed_index", -1)
        start_idx = max(0, last_completed_index + 1)
        print(
            f"[RESUME] Loaded checkpoint {checkpoint_path} | "
            f"last completed chunk index: {last_completed_index}"
        )

    for i in range(start_idx, len(l2_chunks)):
        chunk = l2_chunks[i]
        print(f"[META] {i+1}/{len(l2_chunks)}: {chunk['chunk_id']}")

        try:
            updated = tag_chunk(chunk)
            updated_chunks.append(updated)

        except Exception as e:
            print(f"[ERROR] Failed on {chunk['chunk_id']}: {e}")
            chunk["metadata"] = get_fallback_metadata(chunk["text"])
            updated_chunks.append(chunk)

        finally:
            _save_checkpoint(checkpoint_path, i, updated_chunks)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(updated_chunks, f, indent=2, ensure_ascii=False)

    if checkpoint_path.exists():
        checkpoint_path.unlink()

    print(f"[DONE] Metadata saved to {output_path}")

    return updated_chunks