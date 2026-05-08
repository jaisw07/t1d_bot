import json
from pathlib import Path
from typing import List, Dict

from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)

from tqdm import tqdm

from src.vector.embedding import E5Embedder


# =========================================================
# CONFIG
# =========================================================

COLLECTION_NAME = "ispad_l2_chunks"

VECTOR_DIM = 1024

INDEX_PARAMS = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {
        "M": 32,
        "efConstruction": 200,
    },
}


# =========================================================
# LOAD JSONL
# =========================================================

def load_jsonl(path: str):

    rows = []

    with open(path, "r", encoding="utf-8") as f:

        for line in f:
            rows.append(json.loads(line))

    return rows


# =========================================================
# FILTER L2
# =========================================================

def get_l2_rows(rows):

    return [
        r for r in rows
        if r["chunk_level"] == "L2"
    ]


# =========================================================
# CREATE COLLECTION
# =========================================================

def create_collection():

    if utility.has_collection(COLLECTION_NAME):

        print(f"[INFO] Collection exists: {COLLECTION_NAME}")

        return Collection(COLLECTION_NAME)

    print(f"[INFO] Creating collection: {COLLECTION_NAME}")

    fields = [

        FieldSchema(
            name="id",
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=256,
        ),

        FieldSchema(
            name="embedding",
            dtype=DataType.FLOAT_VECTOR,
            dim=VECTOR_DIM,
        ),

        FieldSchema(
            name="text",
            dtype=DataType.VARCHAR,
            max_length=65535,
        ),

        FieldSchema(
            name="chapter_id",
            dtype=DataType.VARCHAR,
            max_length=64,
        ),

        FieldSchema(
            name="chapter_title",
            dtype=DataType.VARCHAR,
            max_length=512,
        ),

        FieldSchema(
            name="topic",
            dtype=DataType.VARCHAR,
            max_length=128,
        ),

        FieldSchema(
            name="severity",
            dtype=DataType.VARCHAR,
            max_length=64,
        ),
    ]

    schema = CollectionSchema(
        fields=fields,
        description="ISPAD L2 semantic retrieval corpus",
    )

    collection = Collection(
        name=COLLECTION_NAME,
        schema=schema,
    )

    # =====================================================
    # Index
    # =====================================================

    collection.create_index(
        field_name="embedding",
        index_params=INDEX_PARAMS,
    )

    print("[INFO] Index created")

    return collection


# =========================================================
# BUILD EMBEDDINGS + STORE
# =========================================================

def build_milvus_index(
    corpus_path: str,
    milvus_host: str = "localhost",
    milvus_port: str = "19530",
):

    # =====================================================
    # Connect
    # =====================================================

    print("[INFO] Connecting to Milvus...")

    connections.connect(
        alias="default",
        host=milvus_host,
        port=milvus_port,
    )


    # =====================================================
    # Load corpus
    # =====================================================

    print("[INFO] Loading normalized corpus...")

    rows = load_jsonl(corpus_path)

    l2_rows = get_l2_rows(rows)

    print(f"[INFO] L2 rows: {len(l2_rows)}")

    # =====================================================
    # Create embedder
    # =====================================================

    embedder = E5Embedder()

    # =====================================================
    # Create collection
    # =====================================================

    collection = create_collection()

    # =====================================================
    # Prevent duplicate indexing
    # =====================================================

    existing = collection.num_entities

    if existing > 0:

        print(
            f"[INFO] Collection already contains "
            f"{existing} vectors"
        )

        collection.load()

        return collection

    # =====================================================
    # Prepare data
    # =====================================================

    ids = []
    texts = []
    chapter_ids = []
    chapter_titles = []
    topics = []
    severities = []

    for row in l2_rows:

        ids.append(row["retrieval_id"])

        text = row["content"]["text"]

        texts.append(text)

        hierarchy = row["hierarchy"]

        metadata = row.get("metadata", {})

        chapter_ids.append(
            hierarchy.get("chapter_id", "")
        )

        chapter_titles.append(
            hierarchy.get("chapter_title", "")
        )

        topics.append(
            metadata.get("topic", "general")
        )

        severities.append(
            metadata.get("severity", "routine")
        )

    # =====================================================
    # Embeddings
    # =====================================================

    print("[INFO] Generating embeddings...")

    embeddings = embedder.embed_passages(texts)

    print(f"[INFO] Embeddings shape: {embeddings.shape}")

    # =====================================================
    # Insert
    # =====================================================

    print("[INFO] Inserting into Milvus...")

    entities = [
        ids,
        embeddings.tolist(),
        texts,
        chapter_ids,
        chapter_titles,
        topics,
        severities,
    ]

    collection.insert(entities)

    collection.flush()

    collection.load()

    print("\n=================================================")
    print("[DONE] Milvus indexing complete")
    print(f"[COLLECTION] {COLLECTION_NAME}")
    print(f"[VECTORS] {len(ids)}")

    return collection