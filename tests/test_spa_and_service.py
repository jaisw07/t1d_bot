import os
import re
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from src.service import app
from src.corpus_store.store import SearchResult
from src.generation.generator import Response

client = TestClient(app)

def test_static_spa_endpoint_returns_updated_index_html():
    """Verify GET / returns updated index.html with T1D RAGbot title and simplified controls."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "T1D RAGbot" in response.text
    # Subheading should be removed
    assert "Dense-Sparse Hybrid Retrieval & Medical Decision Support System" not in response.text
    assert "system-subtitle" not in response.text

    # Updated labels assertions
    assert "LLM Answer Generation" in response.text
    assert "Number of chunks to retrieve" in response.text
    assert "Language for Retrieved Knowledge Base" in response.text

    # Removed sections assertions
    assert "Filter Parameters" not in response.text
    assert "Database Overview" not in response.text
    assert "filter-collection" not in response.text
    assert "filter-dosage" not in response.text

@patch("src.service.get_corpus_store")
@patch("src.service.get_generator")
@patch("src.service.log_query")
def test_query_endpoint_decodes_hindi_and_logs(mock_log_query, mock_get_generator, mock_get_store):
    """Verify /query endpoint decodes scrambled Hindi and logs query."""
    mock_store = MagicMock()
    # Signature scrambled Hindi text snippet containing "भधुभेह"
    scrambled_title = "भधुभेह ऩहरे"
    scrambled_content = "भधुभेह ऩहरे"
    
    mock_store.search.return_value = [
        SearchResult(
            text=scrambled_content,
            score=0.92,
            source_document="Hindi_Guide.pdf",
            collection="patient_education",
            content_type="education",
            language="hindi",
            topic="insulin",
            start_page=5,
            section_title=scrambled_title,
            keywords=["insulin"],
            contains_dosage=True,
            contains_recommendation=False
        )
    ]
    mock_get_store.return_value = mock_store

    mock_generator = MagicMock()
    mock_generator.generate.return_value = Response(
        answer="Patient education guidance in Hindi.",
        citations=["Hindi_Guide.pdf, p.5"],
        language="hindi"
    )
    mock_get_generator.return_value = mock_generator

    payload = {
        "query": "insulin guidance",
        "language": "hindi",
        "top_k": 1
    }

    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Patient education guidance in Hindi."
    assert len(data["retrieved_chunks"]) == 1
    chunk = data["retrieved_chunks"][0]
    
    # Decoded text should not be equal to raw scrambled text
    assert chunk["section_title"] != scrambled_title
    assert "मधुमेह" in chunk["section_title"]
    
    # Verify log_query was called
    mock_log_query.assert_called_once_with(
        question="insulin guidance",
        answer="Patient education guidance in Hindi.",
        citations=["Hindi_Guide.pdf, p.5"]
    )

def test_static_files_aesthetic_and_content_constraints():
    """Verify static SPA files adhere to no emojis, no blue color codes, and updated loading text."""
    static_dir = os.path.join("src", "static")
    html_path = os.path.join(static_dir, "index.html")
    css_path = os.path.join(static_dir, "styles.css")
    js_path = os.path.join(static_dir, "app.js")

    assert os.path.exists(html_path), "index.html missing"
    assert os.path.exists(css_path), "styles.css missing"
    assert os.path.exists(js_path), "app.js missing"

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()

    combined = html_content + css_content + js_content

    # Emoji regex range check with correct 8-digit unicode escapes
    emoji_pattern = re.compile(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]'
    )
    emojis_found = emoji_pattern.findall(combined)
    assert not emojis_found, f"Emojis found in static files: {set(emojis_found)}"

    # Blue color check
    disallowed_blues = [
        "#3b82f6", "#2563eb", "#1d4ed8", "#60a5fa", "#0000ff", "#00f",
        "#1e40af", "#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe"
    ]
    for b in disallowed_blues:
        assert b.lower() not in css_content.lower(), f"Disallowed blue color {b} found in styles.css"

    # JS loading text assertions
    assert "thinking..." in js_content.lower() or "searching database..." in js_content.lower()

    # Markdown rendering assertion in app.js
    assert "rendermarkdown" in js_content.lower()
