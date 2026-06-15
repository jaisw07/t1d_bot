import json
import os
from pathlib import Path
from .chunker import Chunk

def clean_text(text: str) -> str:
    """Clean up formatting artifacts in text."""
    if not text:
        return ""
    # Replace multiple spaces/newlines with single space
    import re
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize_chunks(chunks: list[Chunk], output_path: str) -> str:
    """Serializes chunks with metadata to the unified master JSONL schema.
    Returns the absolute path to the generated JSONL file.
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    seen_ids = set()
    
    with open(out_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            # Ensure unique retrieval ids
            retrieval_id = chunk.chunk_id
            if retrieval_id in seen_ids:
                # Add unique index if duplicated
                idx = 1
                while f"{retrieval_id}_{idx}" in seen_ids:
                    idx += 1
                retrieval_id = f"{retrieval_id}_{idx}"
            seen_ids.add(retrieval_id)
            
            cleaned_text = clean_text(chunk.text)
            
            # Map source details and metadata safely
            metadata_dict = {}
            source_doc = ""
            collection = ""
            content_type = ""
            language = ""
            
            if chunk.metadata:
                m = chunk.metadata
                source_doc = m.source_document
                collection = m.collection
                content_type = m.content_type
                language = m.language
                metadata_dict = {
                    "content_type": m.content_type,
                    "language": m.language,
                    "topic": m.topic,
                    "keywords": m.keywords,
                    "contains_dosage": m.contains_dosage,
                    "contains_recommendation": m.contains_recommendation
                }
                
            row = {
                "retrieval_id": retrieval_id,
                "chunk_level": "L2",
                "content": {
                    "text": cleaned_text,
                    "token_estimate": len(cleaned_text.split())
                },
                "hierarchy": {
                    "collection": collection,
                    "document": source_doc,
                    "section_title": chunk.section_title,
                    "parent_id": None,
                    "child_ids": chunk.child_ids
                },
                "source": {
                    "start_page": chunk.start_page,
                    "source_document": source_doc
                },
                "metadata": metadata_dict
            }
            
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            
    return str(out_path.resolve())
