# Google Gemini LLM Integration & Deployment Guide

This guide provides instructions and templates for integrating the Google Gemini API (using the newer `google-genai` SDK and REST endpoint) into any Python project.

---

## 1. Prerequisites & Installation

Install the official Google GenAI Python SDK and utility packages:

```bash
pip install google-genai python-dotenv httpx
```

Add your Gemini API key to your environment variables or a `.env` file:
```env
GEMINI_API_KEY=your-api-key-here
```

---

## 2. Client Initialization

Initialize the `genai.Client`. If using a proxy manager (such as the OmniKey Proxy), conditionally configure the `base_url`:

```python
import os
from google import genai
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# Check if routing requests through a custom proxy is required (e.g. OmniKey)
http_opts = (
    {"base_url": "https://omnikey-ai-unified-key-manager.onrender.com"}
    if api_key and api_key.startswith("omnikey")
    else None
)

client = genai.Client(api_key=api_key, http_options=http_opts)
```

---

## 3. General Usage Snippets

### A. Asynchronous Response Streaming (e.g., Chat or Voice applications)
Use the `generate_content_stream` method for real-time text generation. We recommend using `gemini-2.5-flash-lite` for low-latency tasks:

```python
import asyncio
from typing import AsyncGenerator

async def stream_response(prompt: str) -> AsyncGenerator[str, None]:
    stream = client.models.generate_content_stream(
        model="gemini-2.5-flash-lite",
        contents=prompt,
        config={
            "temperature": 0.4,
            "max_output_tokens": 700,
        },
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text
            await asyncio.sleep(0)  # Yield execution to the event loop
```

### B. Structured JSON Generation
Use the `response_mime_type` setting to force the model to return valid JSON. We recommend using `gemini-2.5-flash` for complex reasoning and structured output tasks:

```python
import json

def generate_structured_json(prompt: str) -> dict:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )
        if response.text:
            text = response.text.strip()
            
            # Remove markdown code-block wrappers if present
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            return json.loads(text.strip())
    except Exception as e:
        print(f"Error generating JSON: {e}")
        return {}
```

### C. Direct REST HTTP API Requests (SDK-less)
In environments where you want to keep dependencies to a minimum, perform raw asynchronous POST requests using `httpx`:

```python
import httpx
import json

async def generate_via_rest(prompt: str, api_key: str) -> dict:
    # Determine base URL based on key type
    base_url = (
        "https://omnikey-ai-unified-key-manager.onrender.com"
        if api_key.startswith("omnikey")
        else "https://generativelanguage.googleapis.com"
    )
    url = f"{base_url}/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(url, json=payload, timeout=40.0)
        res_json = response.json()
        raw_text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Clean markdown formatting wrappers
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip())
```
