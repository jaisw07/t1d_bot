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
You are an expert clinical assistant specializing in Type 1 Diabetes (T1D).
Your task is to answer the user's query using ONLY the provided retrieved context.

STRICT RULES:
1. Base your answer solely on the retrieved context below. Do NOT use general knowledge or infer beyond what is explicitly written.
2. If the retrieved context is insufficient to answer the query, reply exactly: "I don't have enough information in the available sources to answer this."
3. Cite your sources inline where you present the facts, using the format [Document Name, p.XX] matching the source document name and page number.
4. Respond in the requested language (e.g., English or Hindi). If language is Hindi, you must write your entire response in Hindi.
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

        model = os.getenv("GENERATION_MODEL", "gemma4:e4b")
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
