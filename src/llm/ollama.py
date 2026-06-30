import ollama
from .client import LLMClient

class OllamaAdapter(LLMClient):
    def __init__(self, host: str = "http://localhost:11434"):
        self._host = host
        self._client = ollama.Client(host=host, timeout=180.0)

    def chat(self, messages: list[dict], model: str, temperature: float = 0.1, max_tokens: int = None) -> str:
        options = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
            
        response = self._client.chat(
            model=model,
            messages=messages,
            options=options,
        )
        return response["message"]["content"]
