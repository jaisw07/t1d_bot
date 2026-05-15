from typing import List, Dict

from pymilvus import (
    connections,
    Collection,
)

from src.vector.embedding import E5Embedder
from src.retrieval.kv_store import HierarchicalKVStore


# =========================================================
# CONFIG
# =========================================================

COLLECTION_NAME = "ispad_l2_chunks"


# =========================================================
# RETRIEVER
# =========================================================

class HierarchicalRetriever:
    """
    Strictly aligned with project methodology:

    Query
        ↓
    multilingual-e5 query embedding
        ↓
    Milvus semantic retrieval (L2 only)
        ↓
    Retrieval expansion:
        - parent context
        - child L3 facts
        ↓
    grounded retrieval package
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        corpus_path: str,
        milvus_host: str = "localhost",
        milvus_port: str = "19530",
        top_k: int = 5,
    ):

        self.top_k = top_k

        # -------------------------------------------------
        # Connect Milvus
        # -------------------------------------------------

        print("[INFO] Connecting to Milvus...")

        connections.connect(
            alias="default",
            host=milvus_host,
            port=milvus_port,
        )

        self.collection = Collection(COLLECTION_NAME)

        self.collection.load()

        print(
            f"[INFO] Loaded collection: "
            f"{COLLECTION_NAME}"
        )

        # -------------------------------------------------
        # Embedder
        # -------------------------------------------------

        self.embedder = E5Embedder()

        # -------------------------------------------------
        # KV Store
        # -------------------------------------------------

        self.kv = HierarchicalKVStore(
            corpus_path=corpus_path
        )

        print("[INFO] Retriever ready")

    # =====================================================
    # VECTOR SEARCH
    # =====================================================

    def vector_search(
        self,
        query: str,
        top_k: int = None,
    ):

        if top_k is None:
            top_k = self.top_k

        # -------------------------------------------------
        # Embed query
        # -------------------------------------------------

        query_embedding = self.embedder.embed_query(query)

        # -------------------------------------------------
        # Search
        # -------------------------------------------------

        search_params = {
            "metric_type": "COSINE",
            "params": {
                "ef": 128
            }
        }

        results = self.collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,

            output_fields=[
                "id",
                "text",
                "chapter_id",
                "chapter_title",
                "topic",
                "severity",
            ],
        )

        return results[0]

    # =====================================================
    # RETRIEVE + EXPAND
    # =====================================================

    def retrieve(
        self,
        query: str,
        top_k: int = None,
    ) -> Dict:

        print("\n========================================")
        print(f"[QUERY] {query}")
        print("========================================")

        results = self.vector_search(
            query=query,
            top_k=top_k,
        )

        retrievals = []

        # -------------------------------------------------
        # Expand hierarchy
        # -------------------------------------------------

        for hit in results:

            entity = hit.entity

            l2_id = entity.get("id")

            expanded = self.kv.expand_l2_chunk(l2_id)

            retrieval_package = {

                "retrieval_id": l2_id,

                "score": float(hit.score),

                # -----------------------------------------
                # Milvus result
                # -----------------------------------------

                "l2_chunk": {

                    "text": entity.get("text"),

                    "chapter_id":
                        entity.get("chapter_id"),

                    "chapter_title":
                        entity.get("chapter_title"),

                    "topic":
                        entity.get("topic"),

                    "severity":
                        entity.get("severity"),
                },

                # -----------------------------------------
                # Expanded hierarchy
                # -----------------------------------------

                "parent_context":
                    expanded.get("parent_context"),

                "l3_facts":
                    expanded.get("l3_facts", []),
            }

            retrievals.append(retrieval_package)

        # -------------------------------------------------
        # Final package
        # -------------------------------------------------

        final_package = {

            "query": query,

            "top_k": len(retrievals),

            "retrievals": retrievals,
        }

        return final_package

    # =====================================================
    # PRETTY PRINT
    # =====================================================

    def pretty_print(
        self,
        retrieval_package: Dict,
        max_l3: int = 3,
    ):

        print("\n")
        print("=" * 80)
        print("RETRIEVAL RESULTS")
        print("=" * 80)

        for idx, r in enumerate(
            retrieval_package["retrievals"],
            start=1,
        ):

            print("\n")
            print("-" * 80)

            print(
                f"[RESULT {idx}] "
                f"score={r['score']:.4f}"
            )

            print("-" * 80)

            l2 = r["l2_chunk"]

            print(
                f"\n[CHAPTER] "
                f"{l2['chapter_title']}"
            )

            print(
                f"\n[TOPIC] "
                f"{l2['topic']}"
            )

            print(
                f"\n[L2 CHUNK]\n"
            )

            print(
                l2["text"][:1200]
            )

            # -------------------------------------------------
            # L3 FACTS
            # -------------------------------------------------

            l3s = r["l3_facts"]

            if l3s:

                print("\n[L3 FACTS]")

                for l3_idx, l3 in enumerate(
                    l3s[:max_l3],
                    start=1,
                ):

                    text = l3["content"]["text"]

                    print(
                        f"\n({l3_idx}) "
                        f"{text[:500]}"
                    )

        print("\n")
        print("=" * 80)