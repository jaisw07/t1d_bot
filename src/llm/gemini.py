import os
from google import genai
from google.genai import types
from .client import LLMClient

class GeminiAdapter(LLMClient):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self._client = genai.Client(
            api_key=api_key,
            http_options={"base_url": "https://omnikey-ai-unified-key-manager.onrender.com"}
        )

    def chat(self, messages: list[dict], model: str, temperature: float = 0.1, max_tokens: int = None) -> str:
        system_instruction = "\n".join([m["content"] for m in messages if m["role"] == "system"])
        if not system_instruction:
            system_instruction = None

        contents = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "model" if m["role"] == "assistant" else m["role"]
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m["content"])]
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens
        )

        response = self._client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )
        return response.text
