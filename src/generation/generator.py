import os
from dataclasses import dataclass
from src.llm.client import LLMClient
from src.corpus_store.store import SearchResult

@dataclass
class Response:
    answer: str
    citations: list[str]
    language: str

SYSTEM_PROMPT = """
You are an expert clinical assistant specializing in Type 1 Diabetes (T1D) patient and caregiver education.
Your goal is to synthesize clear, detailed, highly practical, and structured guidance based on the provided retrieved medical context.

STRICT INSTRUCTIONS:
1. Provide a comprehensive, well-structured answer using bullet points, bold section headings, or clear steps for readability.
2. Do NOT insert inline citation brackets or placeholders (such as [Document Name, p.XX]) inside your text answer. Source citations are automatically tracked and displayed separately by the user interface.
3. Synthesize relevant facts from the retrieved context (e.g., specific food items, glycemic index guidelines, meal planning advice, dosage/monitoring steps) into practical advice.
4. If the user query is in Hindi or Hinglish, provide a clear, supportive response addressing their concerns in the requested language (or clear English with Hindi terms if applicable).
5. Base your information on the retrieved context below. If the context does not fully cover an aspect of the query, answer what is present in the context and gently mention any missing details.
"""

class Generator:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def generate(
        self,
        query: str,
        retrieved_chunks: list[SearchResult],
        language: str = "english"
    ) -> Response:
        """Sends query + context to LLM client, parses answer and maps citations."""
        if not retrieved_chunks:
            return Response(
                answer="I don't have enough information in the available sources to answer this.",
                citations=[],
                language=language
            )

        # 1. Format retrieved contexts
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            context_blocks.append(
                f"--- RETRIEVED CONTEXT [{idx}] ---\n"
                f"Source: {chunk.source_document}, p.{chunk.start_page}\n"
                f"Section: {chunk.section_title}\n"
                f"Content: {chunk.text}\n"
                f"---"
            )
        context_text = "\n\n".join(context_blocks)

        # 2. Build messages and query LLM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Requested Language: {language}\n\nRetrieved Context:\n{context_text}\n\nQuery: {query}"}
        ]

        model = os.getenv("GENERATION_MODEL", "gemma3:1b")
        answer = self._llm.chat(messages, model=model, temperature=0.1).strip()

        # 3. Build deduplicated citations from retrieved chunks
        seen_citations = set()
        citations = []
        for chunk in retrieved_chunks:
            cit = f"{chunk.source_document}, p.{chunk.start_page}"
            if cit not in seen_citations:
                seen_citations.add(cit)
                citations.append(cit)

        return Response(
            answer=answer,
            citations=citations,
            language=language
        )
