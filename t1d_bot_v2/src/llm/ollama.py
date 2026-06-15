import ollama
from .client import LLMClient

class OllamaAdapter(LLMClient):
    def __init__(self, host: str = "http://localhost:11434"):
        self._host = host
        self._client = ollama.Client(host=host)

    def chat(self, messages: list[dict], model: str, temperature: float = 0.1) -> str:
        response = self._client.chat(
            model=model,
            messages=messages,
            options={"temperature": temperature},
        )
        return response["message"]["content"]
