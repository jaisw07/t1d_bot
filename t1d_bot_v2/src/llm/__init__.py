import os
from .client import LLMClient
from .ollama import OllamaAdapter

def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "ollama":
        return OllamaAdapter(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    raise ValueError(f"Unknown LLM provider: {provider}")
