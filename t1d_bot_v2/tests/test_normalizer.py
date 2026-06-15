import os
import json
from src.ingestion.chunker import Chunk
from src.ingestion.metadata_generator import ChunkMetadata
from src.ingestion.normalize import normalize_chunks

def test_normalize_chunks_schema(tmp_path):
    # Arrange
    metadata = ChunkMetadata(
        source_document="Ch1.pdf",
        collection="ispad_2022",
        content_type="guideline",
        language="english",
        topic="epidemiology",
        keywords=["type 1 diabetes"],
        contains_dosage=False,
        contains_recommendation=True
    )
    
    chunks = [
        Chunk(
            chunk_id="Introduction_chunk_1",
            text="Hypoglycemia is a blood glucose level below 70 mg/dL.",
            section_title="Introduction",
            start_page=1,
            end_page=2,
            child_ids=[],
            metadata=metadata
        )
    ]
    
    output_file = os.path.join(tmp_path, "normalized.jsonl")
    
    # Act
    res_path = normalize_chunks(chunks, output_file)
    
    # Assert
    assert res_path == output_file
    assert os.path.exists(output_file)
    
    with open(output_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    assert len(lines) == 1
    data = json.loads(lines[0])
    
    assert data["retrieval_id"] == "Introduction_chunk_1"
    assert data["chunk_level"] == "L2"
    assert data["content"]["text"] == "Hypoglycemia is a blood glucose level below 70 mg/dL."
    assert data["content"]["token_estimate"] > 0
    assert data["hierarchy"]["collection"] == "ispad_2022"
    assert data["hierarchy"]["document"] == "Ch1.pdf"
    assert data["hierarchy"]["section_title"] == "Introduction"
    assert data["hierarchy"]["parent_id"] is None
    assert data["hierarchy"]["child_ids"] == []
    assert data["source"]["start_page"] == 1
    assert data["source"]["source_document"] == "Ch1.pdf"
    assert data["metadata"]["topic"] == "epidemiology"
    assert data["metadata"]["contains_dosage"] is False
    assert data["metadata"]["contains_recommendation"] is True
