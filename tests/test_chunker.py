from src.llm.client import LLMClient
from src.ingestion.structure_detector import Section
from src.ingestion.chunker import Chunker, Chunk

class MockLLMClient(LLMClient):
    def chat(self, messages: list[dict], model: str, temperature: float = 0.1) -> str:
        # Check that we received messages in correct format
        assert len(messages) > 0
        assert "content" in messages[0]
        # Return valid JSON representation of L2 chunks
        return '```json\n[\n  {"text": "Hypoglycemia is defined as a blood glucose level below 70 mg/dL."}\n]\n```'

def test_chunker_basic_chunking():
    # Arrange
    sections = [
        Section(
            title="Hypoglycemia Definition",
            level=2,
            start_page=5,
            end_page=5,
            content=["Hypoglycemia is defined as a blood glucose level below 70 mg/dL."]
        )
    ]
    
    mock_client = MockLLMClient()
    chunker = Chunker(llm_client=mock_client, model="test-model")
    
    # Act
    chunks = chunker.chunk(sections, content_type="guideline")
    
    # Assert
    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, Chunk)
    assert chunk.text == "Hypoglycemia is defined as a blood glucose level below 70 mg/dL."
    assert chunk.section_title == "Hypoglycemia Definition"
    assert chunk.start_page == 5
    assert chunk.end_page == 5
    assert chunk.child_ids == []
    assert len(chunk.chunk_id) > 0
