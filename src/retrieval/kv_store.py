import json
from pathlib import Path
from typing import Dict, List, Optional


class HierarchicalKVStore:
    """
    Hierarchical retrieval store for:

    - L1 parent context
    - L2 semantic chunks
    - L3 atomic facts

    Uses master_corpus.jsonl as source of truth.

    Strictly aligned with project methodology:
    - Milvus stores ONLY L2 vectors
    - KV store stores hierarchy + retrieval expansion data
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        corpus_path: str,
    ):

        self.corpus_path = Path(corpus_path)

        # ---------------------------------------------
        # Primary storage
        # ---------------------------------------------

        self.by_id: Dict = {}

        self.l2_chunks: Dict = {}

        self.l3_chunks: Dict = {}

        # ---------------------------------------------
        # Hierarchy mappings
        # ---------------------------------------------

        self.parent_map: Dict = {}

        self.children_map: Dict = {}

        self.chapter_map: Dict = {}

        # ---------------------------------------------
        # Load corpus
        # ---------------------------------------------

        print("[INFO] Loading KV store...")

        self._load()

        print("[INFO] KV store ready")

        print(f"[INFO] Total chunks: {len(self.by_id)}")
        print(f"[INFO] L2 chunks: {len(self.l2_chunks)}")
        print(f"[INFO] L3 chunks: {len(self.l3_chunks)}")

    # =====================================================
    # LOAD
    # =====================================================

    def _load(self):

        with open(self.corpus_path, "r", encoding="utf-8") as f:

            for line in f:

                row = json.loads(line)

                retrieval_id = row["retrieval_id"]

                # -----------------------------------------
                # Store globally
                # -----------------------------------------

                self.by_id[retrieval_id] = row

                level = row["chunk_level"]

                # -----------------------------------------
                # L2 storage
                # -----------------------------------------

                if level == "L2":

                    self.l2_chunks[retrieval_id] = row

                # -----------------------------------------
                # L3 storage
                # -----------------------------------------

                elif level == "L3":

                    self.l3_chunks[retrieval_id] = row

                # -----------------------------------------
                # Parent mapping
                # -----------------------------------------

                hierarchy = row.get("hierarchy", {})

                parent_id = hierarchy.get("parent_id")

                if parent_id:

                    self.parent_map[retrieval_id] = parent_id

                # -----------------------------------------
                # Child mapping
                # -----------------------------------------

                child_ids = hierarchy.get("child_ids", [])

                self.children_map[retrieval_id] = child_ids

                # -----------------------------------------
                # Chapter grouping
                # -----------------------------------------

                chapter_id = hierarchy.get("chapter_id")

                if chapter_id:

                    if chapter_id not in self.chapter_map:
                        self.chapter_map[chapter_id] = []

                    self.chapter_map[chapter_id].append(
                        retrieval_id
                    )

    # =====================================================
    # BASIC LOOKUP
    # =====================================================

    def get_chunk(
        self,
        retrieval_id: str,
    ) -> Optional[Dict]:

        return self.by_id.get(retrieval_id)

    # =====================================================
    # GET TEXT
    # =====================================================

    def get_text(
        self,
        retrieval_id: str,
    ) -> Optional[str]:

        chunk = self.get_chunk(retrieval_id)

        if not chunk:
            return None

        return chunk["content"]["text"]

    # =====================================================
    # PARENT LOOKUP
    # =====================================================

    def get_parent_id(
        self,
        retrieval_id: str,
    ) -> Optional[str]:

        return self.parent_map.get(retrieval_id)

    def get_parent(
        self,
        retrieval_id: str,
    ) -> Optional[Dict]:

        parent_id = self.get_parent_id(retrieval_id)

        if not parent_id:
            return None

        return self.get_chunk(parent_id)

    # =====================================================
    # CHILD LOOKUP
    # =====================================================

    def get_child_ids(
        self,
        retrieval_id: str,
    ) -> List[str]:

        return self.children_map.get(retrieval_id, [])

    def get_children(
        self,
        retrieval_id: str,
    ) -> List[Dict]:

        child_ids = self.get_child_ids(retrieval_id)

        children = []

        for cid in child_ids:

            chunk = self.get_chunk(cid)

            if chunk:
                children.append(chunk)

        return children

    # =====================================================
    # L2 HELPERS
    # =====================================================

    def get_l2_chunk(
        self,
        retrieval_id: str,
    ) -> Optional[Dict]:

        return self.l2_chunks.get(retrieval_id)

    # =====================================================
    # L3 HELPERS
    # =====================================================

    def get_l3_children(
        self,
        l2_id: str,
    ) -> List[Dict]:

        return self.get_children(l2_id)

    # =====================================================
    # CHAPTER HELPERS
    # =====================================================

    def get_chapter_chunks(
        self,
        chapter_id: str,
    ) -> List[Dict]:

        ids = self.chapter_map.get(chapter_id, [])

        chunks = []

        for cid in ids:

            chunk = self.get_chunk(cid)

            if chunk:
                chunks.append(chunk)

        return chunks

    # =====================================================
    # RETRIEVAL EXPANSION
    # =====================================================

    def expand_l2_chunk(
        self,
        l2_id: str,
    ) -> Dict:
        """
        Expand:
        L2
        + parent context
        + L3 precision facts
        """

        l2 = self.get_l2_chunk(l2_id)

        if not l2:
            return {}

        parent = self.get_parent(l2_id)

        children = self.get_l3_children(l2_id)

        return {

            "l2_chunk": l2,

            "parent_context": parent,

            "l3_facts": children,
        }

    # =====================================================
    # DEBUG / STATS
    # =====================================================

    def stats(self):

        print("\n==============================")
        print("KV STORE STATS")
        print("==============================")

        print(f"Total chunks: {len(self.by_id)}")

        print(f"L2 chunks: {len(self.l2_chunks)}")

        print(f"L3 chunks: {len(self.l3_chunks)}")

        print(f"Parent mappings: {len(self.parent_map)}")

        print(f"Child mappings: {len(self.children_map)}")

        print(f"Chapters: {len(self.chapter_map)}")