# RAG System Architecture & Data Flow

This project implements a medically grounded Retrieval-Augmented Generation (RAG) system for pediatric diabetes care (based on ISPAD Guidelines). The architecture strictly follows a hierarchical chunking, retrieval, and generation methodology to ensure precision and prevent medical hallucinations.

*Note: For deep implementation details, refer to the source files only if required for the current task.*

## System Pipeline Overview

The pipeline consists of four main stages: Ingestion, Storage, Retrieval, and Generation.

### 1. Ingestion & Preprocessing (`src/ingestion/`)
- **PDF Extraction**: Raw text and tables are extracted from PDF guidelines while preserving layout.
- **Chapter Detection**: The document is segmented into chapters using font statistics and heading rules.
- **Hierarchical Chunking**:
  - **L2 Chunks (Semantic)**: Chapters are divided into semantically complete 200-400 token chunks using an LLM.
  - **L3 Chunks (Atomic Facts)**: L2 chunks are further broken down into atomic, standalone facts using an LLM.
- **Metadata Tagging**: L2 chunks are classified via LLM to extract metadata (`severity`, `audience`, `topic`, `contains_dosage`, `contains_recommendation`) to aid in filtering.
- **Normalization**: Cleans noise, standardizes chapter titles, and generates hierarchical IDs linking L2 and L3 chunks.

### 2. Vectorization & Storage (`src/vector/`)
- **Embeddings**: Only L2 (semantic) chunks are embedded using `multilingual-e5-large`.
- **Vector Database**: Embeddings and metadata are indexed in **Milvus** (HNSW index, Cosine similarity).
- **KV Store**: The full hierarchy (L2 chunks, parent contexts, and L3 atomic facts) is stored in a master JSONL file.

### 3. Hierarchical Retrieval (`src/retrieval/`)
- **Vector Search**: The user query is embedded and compared against L2 chunks in Milvus to find the top-k matches.
- **Expansion**: Each retrieved L2 chunk is expanded via the KV store to include:
  - Its parent context.
  - Its specific child L3 atomic facts.
- **Result**: A grounded retrieval package is constructed containing the query, the raw L2 matches, and the expanded hierarchical data.

### 4. Generation (`src/generation/`)
- **Prompt Assembly**: The retrieved package (L2 + L3 + parent context) is formatted into a strict context block. The system prompt heavily penalizes hallucination and forces the model to rely solely on retrieved guidelines.
- **LLM Execution**: The assembled prompt is passed to a local LLM via Ollama (default `gemma4:e4b`) to generate the final response.

## Data Flow Diagram
`PDF` -> `Text Lines` -> `Chapters` -> `L2 Semantic Chunks` -> `L3 Atomic Facts & Metadata` -> `Milvus (L2 Vectors)` & `JSONL (Hierarchy KV)`
`User Query` -> `Streamlit UI` -> `Milvus Search (L2)` -> `Expand via KV (L2 + L3 + Parent)` -> `Prompt Builder` -> `Ollama Generator` -> `Unique Citations & Final Answer` -> `Streamlit UI (Chat + Transparency Expander)`

## Frontend Component
- **Streamlit App (`app.py`)**: Provides a chat interface for mentors.
- **Features**:
  - **Deduplicated Citations**: Unique chapter names displayed as a footer below each response.
  - **Transparency View**: A structured expander showing exactly which L2 chunks and L3 facts were retrieved.
  - **Configurable Retrieval**: Adjustable Top-K settings via sidebar.

## Deployment
For details on running the system locally and exposing it via port forwarding, see [deployment.md](./deployment.md).
