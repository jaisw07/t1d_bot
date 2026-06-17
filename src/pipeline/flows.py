import os
import json
import yaml
from prefect import flow, task
from src.ingestion.parsers.base import DocumentPage
from src.ingestion.structure_detector import Section
from src.ingestion.chunker import Chunk
from src.ingestion.metadata_generator import ChunkMetadata

def load_chunks_from_jsonl(jsonl_path: str) -> list[Chunk]:
    chunks = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            m_data = data.get("metadata", {})
            metadata = ChunkMetadata(
                source_document=data["source"]["source_document"],
                collection=data["hierarchy"]["collection"],
                content_type=m_data.get("content_type", ""),
                language=m_data.get("language", ""),
                topic=m_data.get("topic", ""),
                keywords=m_data.get("keywords", []),
                contains_dosage=m_data.get("contains_dosage", False),
                contains_recommendation=m_data.get("contains_recommendation", False)
            )
            chunk = Chunk(
                chunk_id=data["retrieval_id"],
                text=data["content"]["text"],
                section_title=data["hierarchy"]["section_title"],
                start_page=data["source"]["start_page"],
                end_page=data["source"]["start_page"],
                child_ids=data["hierarchy"]["child_ids"],
                metadata=metadata
            )
            chunks.append(chunk)
    return chunks

@task(retries=2, retry_delay_seconds=30)
def parse_document(source_config: dict, language: str = "english") -> list[DocumentPage]:
    from src.ingestion.parsers.pdf_parser import PDFParser
    from src.ingestion.parsers.docx_parser import DocxParser
    from src.ingestion.parsers.pptx_parser import PptxParser
    
    path = source_config["path"]
    fmt = source_config["format"]
    include_pages = source_config.get("include_pages")
    
    print(f"[parse_document] Parsing {path} (format: {fmt})")
    if fmt == "pdf":
        parser = PDFParser()
        pages = parser.parse(path, include_pages=include_pages, language=language)
    elif fmt == "docx":
        parser = DocxParser()
        pages = parser.parse(path, language=language)
    elif fmt == "pptx":
        parser = PptxParser()
        pages = parser.parse(path, language=language)
    else:
        raise ValueError(f"Unknown format: {fmt}")
                
    return pages

@task(retries=2)
def extract_tables(pages: list[DocumentPage]) -> list[DocumentPage]:
    from src.ingestion.table_extractor import TableExtractor
    print(f"[extract_tables] Extracting tables from {len(pages)} pages")
    extractor = TableExtractor()
    return extractor.extract_tables(pages)

@task(retries=2)
def detect_structure(pages: list[DocumentPage]) -> list[Section]:
    from src.ingestion.structure_detector import StructureDetector
    print(f"[detect_structure] Detecting structure for {len(pages)} pages")
    detector = StructureDetector()
    return detector.detect(pages)

@task(retries=2)
def chunk_sections(sections: list[Section], model: str, content_type: str) -> list[Chunk]:
    from src.ingestion.chunker import Chunker
    from src.llm import get_llm_client
    print(f"[chunk_sections] Chunking {len(sections)} sections with {model}")
    llm = get_llm_client()
    chunker = Chunker(llm_client=llm, model=model)
    return chunker.chunk(sections, content_type)

@task(retries=2)
def generate_metadata_for_chunks(
    chunks: list[Chunk],
    model: str,
    source_doc: str,
    collection: str,
    content_type: str,
    language: str
) -> list[Chunk]:
    from src.ingestion.metadata_generator import MetadataGenerator
    from src.llm import get_llm_client
    print(f"[generate_metadata] Generating metadata for {len(chunks)} chunks with {model}")
    llm = get_llm_client()
    generator = MetadataGenerator(llm_client=llm, model=model)
    for chunk in chunks:
        chunk.metadata = generator.generate(
            chunk_text=chunk.text,
            source_doc=source_doc,
            collection=collection,
            content_type=content_type,
            language=language
        )
    return chunks

@task
def normalize(chunks: list[Chunk], output_file: str) -> str:
    from src.ingestion.normalize import normalize_chunks
    print(f"[normalize] Normalizing {len(chunks)} chunks to {output_file}")
    return normalize_chunks(chunks, output_file)

@task
def embed_and_store(jsonl_path: str, collection_name: str) -> int:
    from src.corpus_store import CorpusStore
    print(f"[embed_and_store] Loading and storing chunks from {jsonl_path} into Milvus collection {collection_name}")
    chunks = load_chunks_from_jsonl(jsonl_path)
    corpus_store = CorpusStore(collection_name=collection_name)
    return corpus_store.store(chunks)

@flow(name="process-source")
def process_source(source_config: dict, collection_config: dict) -> int:
    chunking_model = os.getenv("CHUNKING_MODEL", "gemma4:e4b")
    metadata_model = os.getenv("METADATA_MODEL", "gemma4:e4b")
    milvus_collection = os.getenv("MILVUS_COLLECTION", "t1d_corpus")
    
    pages = parse_document(source_config, language=collection_config.get("language", "english"))
    pages = extract_tables(pages)
    sections = detect_structure(pages)
    
    chunks = chunk_sections(
        sections,
        model=chunking_model,
        content_type=collection_config["content_type"]
    )
    
    source_doc = os.path.basename(source_config["path"])
    chunks = generate_metadata_for_chunks(
        chunks,
        model=metadata_model,
        source_doc=source_doc,
        collection=collection_config["id"],
        content_type=collection_config["content_type"],
        language=collection_config["language"]
    )
    
    source_filename = os.path.splitext(source_doc)[0]
    output_file = f"dataset/normalized/{collection_config['id']}/{source_filename}.jsonl"
    jsonl_path = normalize(chunks, output_file)
    
    count = embed_and_store(jsonl_path, collection_name=milvus_collection)
    return count

@flow(name="process-manifest")
def process_manifest(manifest_path: str = "sources.yaml", limit_one_each: bool = False) -> int:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
        
    collections = manifest.get("collections", [])
    processed_count = 0
    
    for collection in collections:
        for source in collection.get("sources", []):
            if source.get("status") == "pending":
                if limit_one_each:
                    fmt = source.get("format")
                    path = source.get("path")
                    is_smoke_pdf = (fmt == "pdf" and "Ch1-DefinitionEpidemiol.pdf" in path)
                    is_smoke_docx = (fmt == "docx" and "diabetes education full for ward" in path)
                    is_smoke_pptx = (fmt == "pptx" and "Admission and Discharge teaching.pptx" in path)
                    if not (is_smoke_pdf or is_smoke_docx or is_smoke_pptx):
                        continue
                        
                print(f"[process_manifest] Running flow for source: {source['path']}")
                try:
                    count = process_source(source, collection)
                    source["status"] = "processed"
                    print(f"[process_manifest] Ingested {count} chunks successfully")
                except Exception as e:
                    source["status"] = "error"
                    print(f"[process_manifest] Error processing source: {e}")
                    
                # Save updated manifest back to disk
                with open(manifest_path, "w", encoding="utf-8") as f_out:
                    yaml.dump(manifest, f_out, default_flow_style=False)
                    
                processed_count += 1
                
    return processed_count
