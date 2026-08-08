import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from src.service import app
from src.corpus_store.store import SearchResult
from src.generation.generator import Response

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert "collection" in json_data

@patch("src.service.get_corpus_store")
@patch("src.service.get_generator")
def test_query_endpoint_with_filters(mock_get_generator, mock_get_store):
    mock_store = MagicMock()
    mock_store.search.return_value = [
        SearchResult(
            text="Treat hypoglycemia with 15g fast acting carbs.",
            score=0.95,
            source_document="Hypo_Guideline.pdf",
            collection="clinical_guidelines",
            content_type="guideline",
            language="english",
            topic="hypoglycemia",
            start_page=12,
            section_title="Rule of 15",
            keywords=["hypo", "glucose"],
            contains_dosage=True,
            contains_recommendation=True
        )
    ]
    mock_get_store.return_value = mock_store

    mock_generator = MagicMock()
    mock_generator.generate.return_value = Response(
        answer="Give 15 grams of fast-acting glucose and recheck in 15 minutes.",
        citations=["Hypo_Guideline.pdf, p.12"],
        language="english"
    )
    mock_get_generator.return_value = mock_generator

    payload = {
        "query": "how to treat hypo",
        "language": "english",
        "top_k": 3,
        "collection": "clinical_guidelines",
        "content_type": "guideline",
        "contains_dosage": True,
        "contains_recommendation": True,
        "topic": "hypoglycemia"
    }

    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Give 15 grams of fast-acting glucose and recheck in 15 minutes."
    assert data["citations"] == ["Hypo_Guideline.pdf, p.12"]
    assert len(data["retrieved_chunks"]) == 1
    assert data["retrieved_chunks"][0]["source_document"] == "Hypo_Guideline.pdf"

    # Verify search was called with exact parsed filters
    mock_store.search.assert_called_once_with(
        query="how to treat hypo",
        filters={
            "collection": "clinical_guidelines",
            "content_type": "guideline",
            "contains_dosage": True,
            "contains_recommendation": True,
            "topic": "hypoglycemia"
        },
        top_k=3
    )
