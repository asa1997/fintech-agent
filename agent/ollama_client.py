import httpx

OLLAMA_BASE = "http://localhost:11434"
CHAT_MODEL = "llama3.2:latest"  # example; use any local model

async def ollama_chat(messages, model: str = CHAT_MODEL, stream: bool = False):
    payload = {"model": model, "messages": messages, "stream": stream}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()["message"]["content"]