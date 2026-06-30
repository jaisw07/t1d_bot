from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], model: str, temperature: float = 0.1, max_tokens: int = None) -> str:
        """Send messages to the LLM, return the response string."""
        pass
