import pytest
from src.ingestion.chunker import Chunk
from src.ingestion.metadata_generator import ChunkMetadata
from src.corpus_store.store import CorpusStore, SearchResult

class MockEmbedder:
    def embed_text(self, text: str):
        # 1024-dim dense vector and simple sparse vector
        dense = [0.1] * 1024
        sparse = {1: 0.5, 2: 0.3}
        return dense, sparse

    def embed_query(self, text: str):
        return self.embed_text(text)

def test_corpus_store_upsert_and_search(monkeypatch, tmp_path):
    import os
    if os.name == "nt":
        os.rename = os.replace
    db_file = tmp_path / "test_corpus.db"
    monkeypatch.setenv("MILVUS_HOST", str(db_file))
    
    # Arrange
    metadata = ChunkMetadata(
        source_document="test_doc.pdf",
        collection="test_collection",
        content_type="guideline",
        language="english",
        topic="hypoglycemia",
        keywords=["glucagon"],
        contains_dosage=True,
        contains_recommendation=True
    )
    
    chunks = [
        Chunk(
            chunk_id="test_chunk_001",
            text="If blood glucose is below 70 mg/dL, give 15g of glucose.",
            section_title="Emergency Treatment",
            start_page=3,
            end_page=3,
            child_ids=[],
            metadata=metadata
        )
    ]
    
    mock_embedder = MockEmbedder()
    store = CorpusStore(collection_name="test_corpus_store_collection", embedder=mock_embedder)
    
    # Act: Store chunk
    count = store.store(chunks)
    assert count == 1
    
    # Act: Search chunk
    results = store.search(
        query="glucose below 70",
        filters={"collection": "test_collection", "language": "english"},
        top_k=1
    )
    
    # Assert
    assert len(results) == 1
    res = results[0]
    assert isinstance(res, SearchResult)
    assert res.text == "If blood glucose is below 70 mg/dL, give 15g of glucose."
    assert res.source_document == "test_doc.pdf"
    assert res.collection == "test_collection"
    assert res.content_type == "guideline"
    assert res.language == "english"
    assert res.topic == "hypoglycemia"
    assert res.start_page == 3
    assert res.section_title == "Emergency Treatment"
    assert res.keywords == ["glucagon"]
    assert res.contains_dosage is True
    assert res.contains_recommendation is True


def test_corpus_store_milvus_lite(monkeypatch, tmp_path):
    import os
    # Workaround for Milvus Lite Windows bug: os.rename fails if target exists
    monkeypatch.setattr(os, "rename", os.replace)
    
    # Set MILVUS_HOST to a temporary .db file path to trigger Milvus Lite
    db_file = tmp_path / "test_corpus.db"
    monkeypatch.setenv("MILVUS_HOST", str(db_file))
    
    metadata = ChunkMetadata(
        source_document="test_doc.pdf",
        collection="test_collection",
        content_type="guideline",
        language="english",
        topic="hypoglycemia",
        keywords=["glucagon"],
        contains_dosage=True,
        contains_recommendation=True
    )
    
    chunks = [
        Chunk(
            chunk_id="test_chunk_001",
            text="If blood glucose is below 70 mg/dL, give 15g of glucose.",
            section_title="Emergency Treatment",
            start_page=3,
            end_page=3,
            child_ids=[],
            metadata=metadata
        )
    ]
    
    mock_embedder = MockEmbedder()
    store = CorpusStore(collection_name="test_corpus_store_lite", embedder=mock_embedder)
    
    # Act: Store chunk
    count = store.store(chunks)
    assert count == 1
    
    # Act: Search chunk
    results = store.search(
        query="glucose below 70",
        filters={"collection": "test_collection", "language": "english"},
        top_k=1
    )
    
    # Assert
    assert len(results) == 1
    res = results[0]
    assert isinstance(res, SearchResult)
    assert res.text == "If blood glucose is below 70 mg/dL, give 15g of glucose."
    assert res.source_document == "test_doc.pdf"
    assert res.collection == "test_collection"
    assert res.content_type == "guideline"
    assert res.language == "english"
    assert res.topic == "hypoglycemia"
    assert res.start_page == 3
    assert res.section_title == "Emergency Treatment"
    assert res.keywords == ["glucagon"]
    assert res.contains_dosage is True
    assert res.contains_recommendation is True

