import os
import pytest
from unittest.mock import patch
from src.llm import get_llm_client

def test_get_llm_client_raises_value_error_when_gemini_api_key_missing():
    # Arrange: Force LLM_PROVIDER to gemini, and clear GEMINI_API_KEY
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}):
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            get_llm_client()
        
        assert "GEMINI_API_KEY environment variable is required" in str(exc_info.value)

def test_get_llm_client_returns_gemini_adapter():
    from src.llm.gemini import GeminiAdapter
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "fake_key"}):
        client = get_llm_client()
        assert isinstance(client, GeminiAdapter)

@patch("google.genai.Client")
def test_gemini_adapter_initializes_google_genai_client(mock_client_class):
    from src.llm.gemini import GeminiAdapter
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}):
        adapter = GeminiAdapter()
        mock_client_class.assert_called_once_with(
            api_key="test_api_key",
            http_options={"base_url": "https://omnikey-ai-unified-key-manager.onrender.com"}
        )

@patch("google.genai.Client")
def test_gemini_adapter_chat_formats_and_routes_correctly(mock_client_class):
    from src.llm.gemini import GeminiAdapter
    from google.genai import types
    
    mock_client = mock_client_class.return_value
    mock_response = mock_client.models.generate_content.return_value
    mock_response.text = "Mocked answer"

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}):
        adapter = GeminiAdapter()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]
    
    response_text = adapter.chat(
        messages=messages,
        model="gemini-2.5-flash",
        temperature=0.2
    )

    assert response_text == "Mocked answer"

    mock_client.models.generate_content.assert_called_once()
    args, kwargs = mock_client.models.generate_content.call_args
    
    assert kwargs.get("model") == "gemini-2.5-flash"
    
    config = kwargs.get("config")
    assert config is not None
    assert config.system_instruction == "You are a helpful assistant."
    assert config.temperature == 0.2

    contents = kwargs.get("contents")
    assert len(contents) == 3
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "Hello"
    assert contents[1].role == "model"
    assert contents[1].parts[0].text == "Hi there!"
    assert contents[2].role == "user"
    assert contents[2].parts[0].text == "How are you?"
