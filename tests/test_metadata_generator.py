from src.llm.client import LLMClient
from src.ingestion.metadata_generator import MetadataGenerator, ChunkMetadata

class MockLLMClient(LLMClient):
    def chat(self, messages: list[dict], model: str, temperature: float = 0.1, max_tokens: int = None) -> str:
        # Return valid metadata JSON
        return '```json\n{\n  "topic": "hypoglycemia",\n  "keywords": ["low blood sugar", "glucagon"]\n}\n```'

def test_metadata_generator_basic():
    # Arrange
    text = "For severe hypoglycemia, you should administer 15g of glucose."
    mock_client = MockLLMClient()
    generator = MetadataGenerator(llm_client=mock_client, model="test-model")
    
    # Act
    metadata = generator.generate(
        chunk_text=text,
        source_doc="Ch1.pdf",
        collection="ispad_2022",
        content_type="guideline",
        language="english"
    )
    
    # Assert
    assert isinstance(metadata, ChunkMetadata)
    assert metadata.source_document == "Ch1.pdf"
    assert metadata.collection == "ispad_2022"
    assert metadata.content_type == "guideline"
    assert metadata.language == "english"
    assert metadata.topic == "hypoglycemia"
    assert metadata.keywords == ["low blood sugar", "glucagon"]
    
    # Regex triggers
    assert metadata.contains_dosage is True         # triggered by "15g"
    assert metadata.contains_recommendation is True  # triggered by "should"
