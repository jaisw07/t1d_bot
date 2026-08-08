# T1D RAG Bot — Tech Stack & Model Documentation

This document provides a detailed breakdown of the technology stack and AI models used in the **Type 1 Diabetes (T1D) RAG Bot (v2)** system. The RAG system parses multilingual, multi-format medical literature (English and Hindi; PDF, DOCX, and PPTX), indexes content using a hybrid dense-sparse vector representation, and provides a dark-themed Streamlit dashboard for exploration and question answering.

---

## 🤖 AI Models

The system is decoupled from specific LLM provider APIs using an `LLMClient` adapter seam. While the codebase contains structural configuration adapters (such as for Gemini), only local/on-premise models were used during pipeline runs and final deployment, without any cloud dependency.

| Pipeline Stage / Role | Model / Model Version | Deployment / Run Environment | Purpose & Details |
| :--- | :--- | :--- | :--- |
| **Document Embedding** | **BAAI/bge-m3** | Local PyTorch (CPU or GPU) | Computes 1024-dimensional dense vectors (mean pooling/CLS representation) and token-weight sparse vectors (MLM logits) for hybrid dense-sparse search. |
| **Semantic Chunking (L2)** | **gemma4:12b** | Local Ollama (on GPU cluster) | Segments raw section text into semantically cohesive chunks based on content-type guidelines (Guideline: 200-400 tokens; Textbook: 250-500 tokens; Patient Education: 150-300 tokens). Falls back to a character sliding window if LLM chunking fails. |
| **Metadata Generator** | **gemma4:12b** | Local Ollama (on GPU cluster) | Classifies chunk text into one of 18 predefined diabetes-related topics (e.g., `insulin_therapy`, `hypoglycemia`, `dka`) and extracts 2–5 medical keywords. |
| **Response Generation** | **gemma4:12b** | Local Ollama (on GPU cluster) | Generates factually restricted, citation-backed answers strictly using retrieved contexts. Rewrites response completely in Hindi if Hindi queries are requested. |

> [!NOTE]
> The codebase includes an [LLMClient](file:///C:/Users/SHREY/Desktop/t1d_bot/src/llm/client.py#L3) adapter seam that supports a Google Gemini client wrapper (`GeminiAdapter`) as a structural option. However, no cloud provider is used in actual execution or deployment; the Gemini integration exists solely as a code placeholder.

---

## 🏗️ Core Software Stack

The table below outlines the core libraries, orchestration engines, databases, and parsing layers composing the codebase.

| Stack Layer | Software / Library | Version | Purpose & Implementation Details |
| :--- | :--- | :--- | :--- |
| **User Interface** | [Streamlit](https://streamlit.io/) | `>= 1.35.0` | Provides an interactive web dashboard for search queries and QA. Features a dark theme and sidebar filters (Collection, Language, Content Type, and boolean flags for Dosage/Recommendation). |
| **Vector Database** | [Milvus-lite](https://milvus.io/) | `>= 2.4.2` | Runs locally as a portable file-based DB (`t1d_corpus.db`). Windows uses Milvus-lite 3.0 via an automated migration script (`migrate_to_v3.py`), while Linux pods run 2.4.x. |
| **Database Server** | Milvus Standalone | (Docker Compose) | Runs Milvus, MinIO, etcd, and Attu in a WSL2 Docker CE instance for remote ingestion. |
| **Orchestration** | [Prefect](https://www.prefect.io/) | Built-in / Cli | Manages and monitors flow-level and task-level execution of document parsing, chunking, and database inserts. Supports server/UI mode. |
| **PDF Parser** | [PyMuPDF](https://pymupdf.readthedocs.io/) | Built-in | Parses PDF pages, extracts font size features (to compute heading statistics), and handles image/table block identification. |
| **DOCX Parser** | [python-docx](https://python-docx.readthedocs.io/) | `>= 1.1.2` | Extracts text and inline table content directly from MS Word files. |
| **PPTX Parser** | [python-pptx](https://python-pptx.readthedocs.io/) | `>= 1.0.2` | Extracts slide text and native shapes from MS PowerPoint files. |
| **Deep Learning Stack** | [PyTorch](https://pytorch.org/) & [Transformers](https://huggingface.co/docs/transformers) | Latest | Used to run the `BAAI/bge-m3` model locally for embedding generation. Uses GPU (`cuda`) if available, else falls back to CPU. |
| **JSON Serialization** | [Pydantic](https://docs.pydantic.dev/) | `>= 2.10.6` | Defines and validates semantic data schemas for normalized RAG inputs and pipeline assets. |
| **Data Processing** | [Pandas](https://pandas.pydata.org/) | `>= 2.2.3` | Facilitates dataset operations and tabular structure mappings. |
| **Excel Export** | [xlsxwriter](https://xlsxwriter.readthedocs.io/) | `>= 3.2.2` | Used for writing structured outputs to spreadsheet files. |
| **YAML Parser** | [PyYAML](https://pyyaml.org/) | `>= 6.0.2` | Parses and serializes the config manifest file (`sources.yaml`). |

---

## 🔧 Specialty Engines & Utilities

### 1. Hindi Custom Font Decoder (`hindi_decoder.py`)
Many Hindi PDFs (including patient booklets) contain legacy KrutiDev font encoding or custom font layouts, resulting in scrambled text extraction (e.g., `एं जक्टआग` instead of `इंजेक्‍शन`). 
* **Detection:** A heuristic pattern detects legacy character maps.
* **Translation:** A custom translation map matches scrambled character pairs and maps them back into standard Unicode Devanagari script.
* **Execution:** Run both on the **ingestion side** (so BGE-M3 embeds clean Hindi terms) and on the **frontend side** (to display clean readable Hindi on the Streamlit dashboard).

### 2. Heuristic Structure Detector (`structure_detector.py`)
* Computes font size distributions (median and 90th percentile) using `numpy` over all text blocks of a parsed document.
* Classifies blocks as section/sub-section headings or body text using style criteria (font size deviation, bold attributes, uppercase rules, and length checks).

### 3. Annotation & Metadata Classifier Rules (`metadata_generator.py`)
In addition to LLM-inferred topics and keywords, metadata classification features two local regex checkers:
* **Dosage Regex (`DOSAGE_PATTERN`):** Matches medical quantities and units such as `mg`, `mmol/L`, `mU`, `units`, `g/kg`, `IU`, `mL`, `%`, `mg/dL`, `mcg`, `µg`, or `g`.
* **Recommendation Regex (`RECOMMENDATION_KEYWORDS`):** Matches clinical directives (e.g., `should`, `must`, `recommend`, `protocol`, `administer`, `avoid`, `chahiye`, `karein`).

---

## 🗃️ Vector Store Schema & Retrieval

### Hybrid Index Configuration (Milvus)
Milvus indices are generated using separate metric structures to support RRF (Reciprocal Rank Fusion):
1. **Dense Vector Index:**
   * **Field Name:** `dense_embedding` (1024 dimensions)
   * **Metric Type:** `COSINE`
   * **Index Type:** `HNSW` (Parameters: `M=16`, `efConstruction=200`)
2. **Sparse Vector Index:**
   * **Field Name:** `sparse_embedding` (token-weight mappings)
   * **Metric Type:** `IP` (Inner Product)
   * **Index Type:** `SPARSE_INVERTED_INDEX` (Parameters: `drop_ratio_build=0.2`)

### Universal Metadata Schema
Every chunk in the vector store is indexed alongside a common set of metadata fields:
* `id` (VARCHAR)
* `text` (VARCHAR)
* `source_document` (VARCHAR)
* `collection` (VARCHAR)
* `content_type` (VARCHAR)
* `language` (VARCHAR)
* `topic` (VARCHAR)
* `contains_dosage` (BOOL)
* `contains_recommendation` (BOOL)
* `start_page` (INT)
* `section_title` (VARCHAR)
* `keywords` (JSON-serialized VARCHAR)

---

## 🌐 GPU Cluster Deployment

The end-to-end ingestion pipeline (which processed 4,752 chunks) was executed on a remote high-performance GPU cluster.

* **Hardware Partition:** Kubernetes interactive pod (`gpu-interactive` under namespace `dgx-s-bmu-soet-230512-restricted`) running on an **NVIDIA H200 GPU** partition (16 GB VRAM).
* **Local LLM Hosting:** Ollama background process configured to host `gemma4:12b` locally on the pod container.
* **Pipeline Execution:** Run in the background via `nohup` inside `/workspace/t1d_bot/`.
* **Database Transfer & Localization:** The resulting database (`t1d_corpus.db`) was copied to the persistent home directory (`/user-home/`), compressed, and downloaded to the local Windows machine via `scp` for Streamlit dashboard access.

