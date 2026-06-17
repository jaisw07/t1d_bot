import os
from .client import LLMClient
from .ollama import OllamaAdapter

def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "ollama":
        return OllamaAdapter(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    elif provider == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY environment variable is required")
        from .gemini import GeminiAdapter
        return GeminiAdapter()
    raise ValueError(f"Unknown LLM provider: {provider}")


