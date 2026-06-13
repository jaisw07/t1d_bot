# Implementation Plan: Basic Frontend Setup

This plan outlines the steps to implement a Streamlit-based frontend for the T1D RAG bot, enabling remote testing by mentors via local port forwarding.

## 1. Backend Modification
*   **Target:** `src/generation/generate.py`
*   **Action:** Modify `MedicalRAGGenerator.generate` to extract and return a unique list of chapter titles from the retrieval results.
*   **Verification:** Run a test script to ensure `sources` are correctly returned.

## 2. Frontend Implementation
*   **Target:** `app.py` (New)
*   **Framework:** Streamlit
*   **Features:**
    *   **Chat Interface:** `st.chat_message` for conversation history.
    *   **Sidebar Settings:** Top-K slider (default 5).
    *   **Gemma Formatting:** Ensure readable output (Markdown).
    *   **Citations:** "Sources" footer below each response with unique chapter names.
    *   **Transparency:** "Source Context" expander with a structured view:
        *   Chapter Title
        *   L2 Semantic Chunk text
        *   Bulleted L3 Atomic Facts
*   **Verification:** Run `streamlit run app.py` and test end-to-end.

## 3. Context Update
*   **Target:** `context/` directory.
*   **Action:** Update `architecture.md` and `modules.md` to include the frontend component and any data flow changes.

## 4. Documentation & Handover
*   **Action:** Provide the final command for running the app and a reminder for the port forwarding setup.
