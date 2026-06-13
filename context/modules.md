# Module-Wise Breakdown

This document provides a granular breakdown of the key files and classes in the codebase. 

*Note: For deep implementation details, specific prompts, or config values, refer to the files mentioned below **only if required for the current task**.*

## `src/ingestion/` (Data Processing)
- **`pdf_extractor.py`**: Contains `extract_pdf_raw` to extract text blocks and tables using PyMuPDF.
- **`chapter_detector.py`**: Contains `detect_chapters`. Analyzes font sizes and heading patterns to split raw pages into logical chapters.
- **`chunker.py`**: Contains `chunk_document` and `generate_l3_for_file`. Uses a GenAI client (Gemini) to generate L2 and L3 chunks.
  - *Pointer: See `CHUNKING_PROMPT` and `L3_EXTRACTION_PROMPT` in `src/ingestion/chunker.py` **only if required for the current task**.*
- **`metadata_generator.py`**: Contains `tag_chunk` to apply metadata classifications using LLM and rule-based regex overrides.
  - *Pointer: See `METADATA_PROMPT` in `src/ingestion/metadata_generator.py` **only if required for the current task**.*
- **`normalize.py`**: Contains `normalize_dataset`. Cleans up OCR noise and links chunks hierarchically.

## `src/vector/` (Embeddings & DB)
- **`embedding.py`**: Contains `E5Embedder`, a wrapper around `SentenceTransformer` for `intfloat/multilingual-e5-large`. Handles formatting text with `passage:` and `query:` prefixes.
- **`storage.py`**: Contains `build_milvus_index` and `create_collection`. Defines the Milvus schema and handles inserting L2 chunks.

## `src/retrieval/` (Search Pipeline)
- **`kv_store.py`**: Contains `HierarchicalKVStore`. In-memory dictionary mapped from the master corpus JSONL. Used to look up parents and children of specific chunks.
- **`retrieve.py`**: Contains `HierarchicalRetriever`. Connects to Milvus, executes vector search for L2 chunks, and expands results using `HierarchicalKVStore`.

## `src/generation/` (LLM Generation)
- **`prompt_builder.py`**: Contains `build_prompt` and `build_context_block`. Formats the retrieval package into a prompt string.
  - *Pointer: See `SYSTEM_PROMPT` in `src/generation/prompt_builder.py` **only if required for the current task**.*
- **`generate.py`**: Contains `MedicalRAGGenerator`. Orchestrates the retriever and sends the final prompt to the Ollama backend. Now returns unique `sources`.

## Frontend
- **`app.py`**: Streamlit application providing the chat interface, sidebar controls, and hierarchical transparency visualization.

## Deployment
See [deployment.md](./deployment.md) for environment setup and execution instructions.

## `src/testing/` (Evaluation)
- **`evaluate.py`**: Contains `run_evaluation` to process a question bank, run the generator, and save results.
