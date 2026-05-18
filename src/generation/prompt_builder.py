from typing import Dict, List


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a medical retrieval-augmented assistant specialized in
pediatric diabetes care.

You MUST follow these rules strictly:

1. Use ONLY the provided retrieved context.
2. Do NOT hallucinate medical facts.
3. Do NOT invent treatments, dosages, or recommendations.
4. If the answer is not contained in the context,
   explicitly say:
   "The retrieved guidelines do not provide enough
   information to answer this safely."
5. Prefer exact medical wording from the guidelines.
6. Preserve clinical nuance and uncertainty.
7. Do NOT claim to replace professional medical advice.
8. Keep answers medically grounded and concise.
"""


# =========================================================
# HELPERS
# =========================================================

def truncate(
    text: str,
    max_chars: int = 2500,
) -> str:

    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."


# =========================================================
# FORMAT L3 FACTS
# =========================================================

def format_l3_facts(
    l3_facts: List[Dict],
    max_facts: int = 5,
) -> str:

    if not l3_facts:
        return "No atomic facts available."

    lines = []

    for idx, fact in enumerate(
        l3_facts[:max_facts],
        start=1,
    ):

        text = fact["content"]["text"]

        lines.append(
            f"{idx}. {text}"
        )

    return "\n".join(lines)


# =========================================================
# BUILD CONTEXT BLOCK
# =========================================================

def build_context_block(
    retrieval: Dict,
) -> str:

    l2 = retrieval["l2_chunk"]

    parent = retrieval.get("parent_context")

    l3_facts = retrieval.get("l3_facts", [])

    score = retrieval.get("score", 0)

    lines = []

    lines.append("=" * 80)

    lines.append(
        f"RETRIEVAL SCORE: {score:.4f}"
    )

    lines.append(
        f"CHAPTER: {l2.get('chapter_title', 'Unknown')}"
    )

    lines.append(
        f"TOPIC: {l2.get('topic', 'general')}"
    )

    lines.append("")

    # -----------------------------------------------------
    # Parent context
    # -----------------------------------------------------

    if parent:

        parent_text = parent["content"]["text"]

        lines.append("[PARENT CONTEXT]")
        lines.append(
            truncate(parent_text, 1200)
        )
        lines.append("")

    # -----------------------------------------------------
    # L2 chunk
    # -----------------------------------------------------

    lines.append("[SEMANTIC CONTEXT - L2]")
    lines.append(
        truncate(l2["text"], 2000)
    )

    lines.append("")

    # -----------------------------------------------------
    # L3 facts
    # -----------------------------------------------------

    lines.append("[ATOMIC FACTS - L3]")

    lines.append(
        format_l3_facts(l3_facts)
    )

    lines.append("")

    return "\n".join(lines)


# =========================================================
# BUILD FULL PROMPT
# =========================================================

def build_prompt(
    query: str,
    retrieval_package: Dict,
    max_retrievals: int = 3,
) -> str:

    retrievals = retrieval_package["retrievals"]

    selected = retrievals[:max_retrievals]

    context_blocks = []

    for retrieval in selected:

        block = build_context_block(
            retrieval
        )

        context_blocks.append(block)

    combined_context = "\n\n".join(
        context_blocks
    )

    prompt = f"""
{SYSTEM_PROMPT}

===============================================================================
RETRIEVED GUIDELINE CONTEXT
===============================================================================

{combined_context}

===============================================================================
USER QUESTION
===============================================================================

{query}

===============================================================================
ANSWER INSTRUCTIONS
===============================================================================

- Use ONLY the retrieved guideline context.
- If evidence is insufficient, say so explicitly.
- Do NOT invent clinical recommendations.
- Mention uncertainty when appropriate.
- Keep the answer medically grounded.
- Prefer concise evidence-based responses.
- If relevant, mention when medical supervision is required.

===============================================================================
ANSWER
===============================================================================
"""

    return prompt.strip()