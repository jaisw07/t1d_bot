from src.llm.client import LLMClient
from src.corpus_store.store import SearchResult
from src.generation.generator import Generator, Response

class MockLLMClient(LLMClient):
    def chat(self, messages: list[dict], model: str, temperature: float = 0.1) -> str:
        # Check system prompt / context instruction
        assert len(messages) >= 2
        # Return mock answer
        return "Hypoglycemia is treated with 15g of glucose [test_doc.pdf, p.3]."

def test_generator_basic():
    # Arrange
    chunks = [
        SearchResult(
            text="If blood glucose is below 70 mg/dL, give 15g of glucose.",
            score=0.9,
            source_document="test_doc.pdf",
            collection="ispad_2022",
            content_type="guideline",
            language="english",
            topic="hypoglycemia",
            start_page=3,
            section_title="Emergency Treatment",
            keywords=["glucagon"],
            contains_dosage=True,
            contains_recommendation=True
        )
    ]
    
    mock_client = MockLLMClient()
    generator = Generator(llm_client=mock_client)
    
    # Act
    res = generator.generate(
        query="how to treat hypoglycemia",
        retrieved_chunks=chunks,
        language="english"
    )
    
    # Assert
    assert isinstance(res, Response)
    assert "treated with 15g of glucose" in res.answer
    assert res.citations == ["test_doc.pdf, p.3"]
    assert res.language == "english"
