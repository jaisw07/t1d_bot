# T1D RAG Bot — Redesign V2 Status Report

We have implemented the core components and verified the end-to-end pipeline using the PDF document type.

---

## 🛠️ Implemented Components

| Phase | Module | Status | Verification (TDD Suite & Smoke Test) |
|---|---|---|---|
| **Step 1** | Config & Manifest | **Done** | Validated `sources.yaml` & `.env` |
| **Step 2** | `LLMClient` Wrapper | **Done** | [test_pdf_parser.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_pdf_parser.py)<br/>[test_gemini.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_gemini.py) |
| **Step 3** | PDF, DOCX, & PPTX Parsers | **Done** | [test_pdf_parser.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_pdf_parser.py)<br/>[test_docx_parser.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_docx_parser.py)<br/>[test_pptx_parser.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_pptx_parser.py)<br/>*Fix: Implemented robust page/slide-level KrutiDev to Unicode conversion for Hindi documents.* |
| **Step 4** | Structure Detector | **Done** | [test_structure_detector.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_structure_detector.py)<br/>*Fix: Ignore non-alphanumeric heading candidates (like layout grids).* |
| **Step 5** | Table Extractor | **Done** | [test_table_extractor.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_table_extractor.py) |
| **Step 6** | Semantic Chunker (L2) | **Done** | [test_chunker.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_chunker.py)<br/>*Fix: Implemented sliding character-window fallback if LLM chunking fails.* |
| **Step 7** | Metadata Generator | **Done** | [test_metadata_generator.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_metadata_generator.py) |
| **Step 8** | Normalizer (JSONL Schema) | **Done** | [test_normalizer.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_normalizer.py) |
| **Step 9** | `CorpusStore` (Milvus / BGE-M3) | **Done** | [test_corpus_store.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_corpus_store.py)<br/>*Fix: Routed filters correctly inside AnnSearchRequest for hybrid search.* |
| **Step 10** | `Generator` (Prompts / Citations) | **Done** | [test_generator.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_generator.py) |
| **Step 11** | End-to-End Ingestion Flow | **Done** | [flows.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/pipeline/flows.py) & [run.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/pipeline/run.py) |
| **Step 12** | Verify PPTX Ingestion (Single File) | **Done** | [test_pptx_parser.py](file:///C:/Users/SHREY/Desktop/t1d_bot/tests/test_pptx_parser.py)<br/>*Fix: Sanitize and truncate chunk ID prefix to prevent Milvus VARCHAR limit error.* |
| **Step 13** | Run Full Ingestion & Localize | **Done** | Ingested complete corpus (4,752 chunks) on GPU pod.<br/>*Fix: Created `migrate_to_v3.py` to convert the 2.4 database to Milvus-lite 3.0 on Windows, resolving the `manifest references missing data file` error.* |
| **Step 14** | Streamlit UI Implementation | **Done** | [dashboard.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/dashboard.py)<br/>*Features: Dark-themed retrieval explorer with filters for Collection, Language, Content Type, and Dosage/Rec flags.* |

---

## 🚦 Verification Results

* **Unit & Integration Tests:** All 14 tests pass successfully.
* **WSL2 Docker CE Migration:**
  * Successfully migrated database services (Milvus standalone, MinIO, etcd, Attu) from Windows Docker Desktop to Docker CE on WSL2 (Ubuntu).
  * Port forwarding verified: Windows python code connects to `localhost:19530` seamlessly.
* **Full Ingestion & Local Migration (Step 13):**
  * The entire corpus defined in `sources.yaml` was successfully ingested on the GPU pod, producing 4,752 chunks.
  * The database was transferred to the local Windows machine, and [migrate_to_v3.py](file:///C:/Users/SHREY/Desktop/t1d_bot/scratch/migrate_to_v3.py) was run to migrate it to Milvus 3.0.
  * Solved the `os.rename` Windows permission error and `_seq` unexpected field insertion error during migration.
  * Verified database query success with no warnings.
* **Streamlit UI Explorer (Step 14):**
  * Implemented a premium dark-themed dashboard at [dashboard.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/dashboard.py).
  * Successfully verified multi-format, multi-language retrieval.
* **Hindi Custom Font Decoding:**
  * Created [hindi_decoder.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/ingestion/hindi_decoder.py) to resolve legacy custom font mapping issues in the patient booklet PDF.
  * Successfully integrated it into [pdf_parser.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/ingestion/parsers/pdf_parser.py) (ingestion-side clean text mapping) and [dashboard.py](file:///C:/Users/SHREY/Desktop/t1d_bot/src/dashboard.py) (frontend rendering fallback).
  * Decodes scrambled text (e.g., `एं जक्टआग` ➔ `इंजेक्शन`, `इआसुलरन` ➔ `इंसुलिन`) into grammatically correct Devanagari Unicode.

---

## 🎯 Next Steps

1. **Step 15: Chat Integration & Generation**
   * Expand the Streamlit app from a retrieval explorer to a full conversational QA bot using the `Generator` module.
2. **Step 16: Evaluation Suite**
   * Implement a quantitative RAG evaluation framework (e.g., Ragas) to measure retrieval recall and generation correctness.
