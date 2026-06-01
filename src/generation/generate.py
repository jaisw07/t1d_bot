import ollama

from src.generation.prompt_builder import (
    build_prompt,
)

from src.retrieval.retrieve import (
    HierarchicalRetriever,
)


# =========================================================
# GENERATOR
# =========================================================

class MedicalRAGGenerator:
    """
    Grounded medical RAG generator.

    Strictly aligned with methodology:
    retrieval
        ↓
    hierarchical expansion
        ↓
    grounded prompt assembly
        ↓
    constrained generation
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        corpus_path: str,
        model_name: str = "gemma4:e4b",
        milvus_host: str = "localhost",
        milvus_port: str = "19530",
        top_k: int = 5,
    ):

        self.model_name = model_name

        # -------------------------------------------------
        # Retriever
        # -------------------------------------------------

        self.retriever = HierarchicalRetriever(
            corpus_path=corpus_path,
            milvus_host=milvus_host,
            milvus_port=milvus_port,
            top_k=top_k,
        )

        print(
            f"[INFO] Using Ollama model: "
            f"{model_name}"
        )

    # =====================================================
    # GENERATE
    # =====================================================

    def generate(
        self,
        query: str,
        top_k: int = None,
        max_retrievals: int = 3,
        temperature: float = 0.2,
    ):

        # -------------------------------------------------
        # Retrieval
        # -------------------------------------------------

        retrieval_package = self.retriever.retrieve(
            query=query,
            top_k=top_k,
        )

        # -------------------------------------------------
        # Prompt
        # -------------------------------------------------

        prompt = build_prompt(
            query=query,
            retrieval_package=retrieval_package,
            max_retrievals=max_retrievals,
        )

        # -------------------------------------------------
        # Ollama generation
        # -------------------------------------------------

        response = ollama.chat(

            model=self.model_name,

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            options={
                "temperature": temperature,
            }
        )

        answer = response["message"]["content"]

        # -------------------------------------------------
        # Final package
        # -------------------------------------------------

        return {

            "query": query,

            "answer": answer,

            "retrieval_package":
                retrieval_package,

            "prompt": prompt,
        }

    # =====================================================
    # PRETTY PRINT
    # =====================================================

    def pretty_print(
        self,
        result: dict,
    ):

        print("\n")
        print("=" * 80)
        print("QUESTION")
        print("=" * 80)

        print(result["query"])

        print("\n")
        print("=" * 80)
        print("ANSWER")
        print("=" * 80)

        print(result["answer"])

        print("\n")
        print("=" * 80)