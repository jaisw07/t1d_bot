import json
import os
from dataclasses import dataclass
from pymilvus import MilvusClient, DataType, RRFRanker, AnnSearchRequest
from src.ingestion.chunker import Chunk
from .schema import get_milvus_schema

@dataclass
class SearchResult:
    text: str
    score: float
    source_document: str
    collection: str
    content_type: str
    language: str
    topic: str
    start_page: int
    section_title: str
    keywords: list[str]
    contains_dosage: bool
    contains_recommendation: bool

def build_expr(filters: dict | None) -> str:
    """Translate dict filters into Milvus boolean expression string."""
    if not filters:
        return ""
    expr_parts = []
    for k, v in filters.items():
        if v is None:
            continue
        if isinstance(v, str):
            expr_parts.append(f'{k} == "{v}"')
        elif isinstance(v, bool):
            expr_parts.append(f'{k} == {str(v).lower()}')
        elif isinstance(v, (int, float)):
            expr_parts.append(f'{k} == {v}')
        elif isinstance(v, list):
            items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in v)
            expr_parts.append(f'{k} in [{items}]')
    return " and ".join(expr_parts)

class CorpusStore:
    def __init__(self, collection_name: str = "t1d_corpus", embedder=None):
        self.collection_name = collection_name
        self.embedder = embedder
        
        # Connect to Milvus Client
        host = os.getenv("MILVUS_HOST", "localhost")
        port = os.getenv("MILVUS_PORT", "19530")
        self.client = MilvusClient(uri=f"http://{host}:{port}")
        
        self._init_collection()

    def _init_collection(self):
        """Initialize collection and index if they do not exist."""
        if self.client.has_collection(self.collection_name):
            return
            
        # Create collection using schema
        schema = get_milvus_schema()
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema
        )
        
        # Prepare and create indexes
        index_params = self.client.prepare_index_params()
        
        index_params.add_index(
            field_name="dense_embedding",
            metric_type="COSINE",
            index_type="HNSW",
            index_name="dense_idx",
            params={"M": 16, "efConstruction": 200}
        )
        
        index_params.add_index(
            field_name="sparse_embedding",
            metric_type="IP",
            index_type="SPARSE_INVERTED_INDEX",
            index_name="sparse_idx",
            params={"drop_ratio_build": 0.2}
        )
        
        self.client.create_index(
            collection_name=self.collection_name,
            index_params=index_params
        )

    def store(self, chunks: list[Chunk]) -> int:
        """Embed and upsert chunks into Milvus. Returns count of chunks stored."""
        if not chunks:
            return 0
            
        data_to_insert = []
        for chunk in chunks:
            if not chunk.metadata:
                continue
                
            dense_vec, sparse_vec = self.embedder.embed_text(chunk.text)
            
            # Serialize keywords list to JSON string
            keywords_str = json.dumps(chunk.metadata.keywords)
            
            row = {
                "id": chunk.chunk_id,
                "dense_embedding": dense_vec,
                "sparse_embedding": sparse_vec,
                "text": chunk.text,
                "source_document": chunk.metadata.source_document,
                "collection": chunk.metadata.collection,
                "content_type": chunk.metadata.content_type,
                "language": chunk.metadata.language,
                "topic": chunk.metadata.topic,
                "contains_dosage": chunk.metadata.contains_dosage,
                "contains_recommendation": chunk.metadata.contains_recommendation,
                "start_page": chunk.start_page,
                "section_title": chunk.section_title,
                "keywords": keywords_str
            }
            data_to_insert.append(row)
            
        if data_to_insert:
            # Idempotent upsert: delete existing primary keys before insert
            pkeys = [r["id"] for r in data_to_insert]
            # In MilvusClient, we can use delete(collection_name, pkeys)
            try:
                self.client.delete(collection_name=self.collection_name, ids=pkeys)
            except Exception:
                pass
                
            self.client.insert(
                collection_name=self.collection_name,
                data=data_to_insert
            )
            # Flush and load collection to guarantee search consistency
            try:
                self.client.flush(collection_name=self.collection_name)
            except Exception:
                pass
            self.client.load_collection(collection_name=self.collection_name)
            
        return len(data_to_insert)

    def search(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 5
    ) -> list[SearchResult]:
        """Embed query, run BGE-M3 hybrid search with metadata filters, return results."""
        # Ensure collection is loaded before search
        self.client.load_collection(collection_name=self.collection_name)
        dense_query, sparse_query = self.embedder.embed_query(query)
        expr = build_expr(filters)
        
        req_dense = AnnSearchRequest(
            data=[dense_query],
            anns_field="dense_embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k
        )
        
        req_sparse = AnnSearchRequest(
            data=[sparse_query],
            anns_field="sparse_embedding",
            param={"metric_type": "IP", "params": {}},
            limit=top_k
        )
        
        output_fields = [
            "text", "source_document", "collection", "content_type", 
            "language", "topic", "start_page", "section_title", 
            "keywords", "contains_dosage", "contains_recommendation"
        ]
        
        res = self.client.hybrid_search(
            collection_name=self.collection_name,
            reqs=[req_dense, req_sparse],
            ranker=RRFRanker(),
            limit=top_k,
            output_fields=output_fields,
            filter=expr
        )
        
        search_results = []
        if res and len(res) > 0:
            # hybrid_search returns a list of results (one per query, since we passed one query, we check index 0)
            hits = res[0]
            for hit in hits:
                entity = hit.get("entity", {})
                
                # Deserialize keywords list
                keywords_str = entity.get("keywords", "[]")
                try:
                    keywords = json.loads(keywords_str)
                except Exception:
                    keywords = []
                    
                search_results.append(SearchResult(
                    text=entity.get("text", ""),
                    score=float(hit.get("distance", 0.0)),
                    source_document=entity.get("source_document", ""),
                    collection=entity.get("collection", ""),
                    content_type=entity.get("content_type", ""),
                    language=entity.get("language", ""),
                    topic=entity.get("topic", ""),
                    start_page=int(entity.get("start_page", 0)),
                    section_title=entity.get("section_title", ""),
                    keywords=keywords,
                    contains_dosage=bool(entity.get("contains_dosage", False)),
                    contains_recommendation=bool(entity.get("contains_recommendation", False))
                ))
                
        return search_results
