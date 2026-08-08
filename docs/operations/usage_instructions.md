# T1D RAG Bot — Pipeline Usage & Configuration Guide

This guide details how to manage document sources, configure LLM models, execute the ingestion pipeline, and adjust parameters within the T1D RAG system.

---

## 1. Managing Document Sources

Sources are defined hierarchically in [sources.yaml](file:///C:/Users/SHREY/Desktop/t1d_bot/sources.yaml) under collections.

### Manifest Schema

```yaml
collections:
  - id: "ispad_2022" # Unique collection identifier
    name: "ISPAD 2022 Guidelines" # Descriptive name
    content_type: "guideline" # Determines chunking prompt (guideline, textbook, patient_education)
    language: "english" # Document language (english, hindi)
    sources:
      - format: "pdf" # Format: pdf, docx, or pptx
        path: "dataset/.../Ch1.pdf" # Workspace-relative file path
        status: "pending" # Status: pending, processed, or error
        include_pages: [1, 2, 3] # Optional: Specific pages or ranges (PDF only)
```

> [!NOTE]
> The ingestion pipeline only processes sources with `status: pending`. Upon successful ingestion, the pipeline updates their status in the file to `processed` (or `error` if a failure occurs).

---

## 2. LLM Selection & Environment Configuration

Copy or edit the [.env](file:///C:/Users/SHREY/Desktop/t1d_bot/.env) file in the project root to select models and configure endpoints.

```env
# ==============================================================================
# LLM Provider Configuration
# Set to 'ollama' or 'gemini'
# ==============================================================================
LLM_PROVIDER=ollama

# ------------------------------------------------------------------------------
# Option A: Ollama Configuration (Local Models)
# ------------------------------------------------------------------------------
OLLAMA_HOST=http://localhost:11434
CHUNKING_MODEL=gemma4:e4b
METADATA_MODEL=gemma4:e4b
GENERATION_MODEL=gemma4:e4b

# ------------------------------------------------------------------------------
# Option B: Gemini Configuration (Cloud Models)
# ------------------------------------------------------------------------------
# GEMINI_API_KEY=your-api-key-here
# CHUNKING_MODEL=gemini-2.5-flash
# METADATA_MODEL=gemini-2.5-flash-lite
# GENERATION_MODEL=gemini-2.5-flash

# ==============================================================================
# Shared Database & Embedding Configuration
# ==============================================================================
EMBEDDING_MODEL=BAAI/bge-m3

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=t1d_corpus

# Prefect
PREFECT_SERVER_ANALYTICS_ENABLED=False
```

- **Provider Options:**
  - `ollama`: Uses local models serviced by Ollama.
  - `gemini`: Uses Google Gemini API (calls are routed through the OmniKey proxy manager configured in the [Gemini adapter](file:///C:/Users/SHREY/Desktop/t1d_bot/src/llm/gemini.py)).

---

## 3. Prerequisites & Environment Setup

Before running the ingestion pipeline, ensure your runtime environment and databases are active:

### A. Conda Environment
Activate the correct Python Conda environment:
```bash
conda activate t1d
```

### B. Docker (Milvus Vector DB via WSL2 Docker CE)
The database services run inside a lightweight **Docker CE** installation on **WSL2 (Ubuntu)** instead of Windows Docker Desktop. Localhost ports are automatically forwarded, allowing Windows clients to connect seamlessly.

1. Open your **WSL2 Ubuntu Terminal**.
2. Navigate to the compose directory and spin up the containers:
   ```bash
   cd ~/milvus
   docker compose up -d
   ```
3. Verify containers are active:
   ```bash
   docker ps
   ```
You can access the Attu database management viewer visually on your Windows host at `http://localhost:8000`.

---

## 4. Running the Ingestion Pipeline

You can run the ingestion pipeline in either **Direct Mode** (runs immediately in the console) or **Server/UI Mode** (runs and monitors through a local Prefect dashboard).

### Option A: Direct Mode (Fastest, Runs In-Console)
Run the script to immediately start ingestion in the foreground:
```bash
# Ingest all pending documents in sources.yaml
python -m src.pipeline.run

# Ingest only smoke-test documents (one of each file format: PDF, DOCX, PPTX)
python -m src.pipeline.run --smoke-test

# Ingest a specific document (must be defined in sources.yaml)
python -m src.pipeline.run --path "dataset/understanding diabetes/ud01.pdf"
```

### Option B: Server Mode (Prefect Dashboard UI)
To monitor execution visually through the Prefect UI, you can spin up a local server:

1. **Start the Prefect Server** (in a dedicated terminal):
   ```bash
   prefect server start --port 4201
   ```
   *Dashboard UI is served at `http://127.0.0.1:4201`.*

2. **Point the Prefect Client to the Server Port** (run once globally on new devices):
   ```bash
   prefect config set PREFECT_API_URL="http://127.0.0.1:4201/api"
   ```

3. **Register & Serve the Flow** (in your workspace terminal):
   ```bash
   # Spins up the worker serving the process-manifest flow
   python -m src.pipeline.run --serve
   ```

4. **Trigger Ingestion Run** (in another terminal or directly via the Web Dashboard):
   ```bash
   prefect deployment run 'process-manifest/t1d-manifest-ingestion'
   ```

---
 
## 5. Local Database Localization & Retrieval Dashboard
 
For local testing and dashboard exploration, you can retrieve the database generated on the GPU pod:
 
### A. Downloading the Database
Since Windows `scp` can fail on deeply nested directories (like Milvus stores), it is highly recommended to compress the database on the remote headnode first before downloading:
 
1. **On the GPU Pod / Remote Headnode:**
   ```bash
   tar -czvf t1d_corpus.tar.gz t1d_corpus.db
   ```
2. **On your local Windows laptop:**
   ```powershell
   # Download the tarball
   scp dgx-s-bmu-soet-230512@10.1.0.176:~/t1d_corpus.tar.gz C:\Users\SHREY\Desktop\t1d_bot\
 
   # Extract the tarball
   tar -xzvf C:\Users\SHREY\Desktop\t1d_bot\t1d_corpus.tar.gz -C C:\Users\SHREY\Desktop\t1d_bot\
   ```
 
### B. Migrating Database for Windows (Milvus-lite 3.0 Mismatch)
Windows only supports `milvus-lite` version **3.0** (with different directory structures and binary WAL files), whereas the Linux GPU pod runs version **2.4.x**. Directly loading the 2.4 database folder on Windows will cause Milvus-lite 3.0 to reject and delete the `.parquet` segment files.
 
To migrate the database locally:
1. Run the local migration script:
   ```powershell
   python scratch/migrate_to_v3.py
   ```
   *This script reads the raw `.parquet` segment files and inserts them directly into a new Milvus 3.0 database (`t1d_corpus.db`), preserving all pre-computed embeddings.*
 
### C. Running the Streamlit Dashboard
To run the interactive retrieval dashboard:
1. Ensure the `streamlit` dependency is installed:
   ```powershell
   pip install -r requirements.txt
   ```
2. Launch the dashboard:
   ```powershell
   streamlit run src/dashboard.py
   ```
   The dashboard will automatically detect the local `t1d_corpus.db` and load it. You can filter by Collection ID, Language, Content Type, and flags (Dosage/Recommendation).
 
### D. Handling Hindi Custom Font Encodings
Some Hindi source documents (such as `Final Hindi booklet.pdf`) use custom or legacy font layouts that extract as scrambled Devanagari characters (e.g., `एं जक्टआग` instead of `इंजेक्शन`, `इआसुलरन` instead of `इंसुलिन`).
 
The RAG system resolves this at two layers:
1. **Ingestion Layer:** The pipeline checks if the extracted text is scrambled using `is_scrambled_hindi()` and translates it back into clean Unicode Devanagari using `src/ingestion/hindi_decoder.py` before chunking and embedding. This ensures the **BGE-M3** model embeds correct Hindi terms for accurate retrieval.
2. **Frontend Layer (Dashboard):** As a fallback safety net, [dashboard.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/dashboard.py) also runs the decoder on-the-fly when rendering retrieved chunks and section titles, guaranteeing that the user always sees clean, readable Hindi.
 
---
 
## 6. Fine-Tuning & Parameter Adjustments

### A. Semantic Chunking
To adjust prompt rules, token boundaries, and fallback chunk sizes:
* **Prompts:** Edit `CHUNKING_PROMPTS` in [chunker.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/ingestion/chunker.py).
* **Token Counts:** Prompts target boundaries based on `content_type`:
  - `guideline`: 200–400 tokens
  - `textbook`: 250–500 tokens
  - `patient_education`: 150–300 tokens
* **Fallback Sliding Window:** If the LLM chunking call fails, a character-based fallback (default: size `1500` characters, overlap `200` characters) is invoked in [chunker.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/ingestion/chunker.py#L150-L162).

### B. Metadata Heuristics
Edit [metadata_generator.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/ingestion/metadata_generator.py) to change:
* **Dosage Regex (`DOSAGE_PATTERN`):** Matches quantities like `mg`, `IU`, `mmol/L`.
* **Recommendation Regex (`RECOMMENDATION_KEYWORDS`):** Triggers flag if recommendation verbs (such as `should`, `must`, `karein`, `chahiye`) are matched.
* **Allowed Topics:** To expand classification labels, update the `allowed_topics` set.

### C. Vector DB Indexing & Search Ranks
Edit [store.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/corpus_store/store.py) to configure:
* **HNSW Metrics:** Customize dense index variables (e.g., `M: 16`, `efConstruction: 200`).
* **Hybrid Search Ranker:** Uses `RRFRanker` (Reciprocal Rank Fusion) to merge dense and sparse results. Adjust search limits or metric parameters in `CorpusStore.search()`.

### D. Generator Prompt & Temperature
Edit [generator.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/generation/generator.py) to customize:
* **Generation Prompt (`SYSTEM_PROMPT`):** Enforces strict reliance on context and language restrictions.
* **Retrieval Limits:** Change the `top_k` query limit inside search calls.
* **Temperature:** Configured as `0.1` by default for high-factual correctness.

---

## 7. Running Tests

To verify setup and integrations, run the test suite with `python -m pytest` (ensuring `src` is added to the PYTHONPATH):

```bash
python -m pytest tests/
```
