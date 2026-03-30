import json
from .ollama_client import ollama_chat

async def classify_intent(message: str) -> str:
    # LLM-based, intentionally easy to manipulate.
    prompt = f"""
Return JSON only:
{{"intent":"query"}} or {{"intent":"complaint"}}

User message:
{message}
"""
    out = await ollama_chat([{"role": "user", "content": prompt}])
    try:
        data = json.loads(out)
        return data.get("intent", "query")
    except Exception:
        return "query"