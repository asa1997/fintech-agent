from .intent_classifier import classify_intent
from .ollama_client import ollama_chat

ESCALATION_TEXT = "This issue requires further investigation. I’m escalating this to our support team."

async def handle_message(services, customer_id: str, message: str) -> str:
    intent = await classify_intent(message)

    if intent == "complaint":
        return ESCALATION_TEXT

    # Query flow: call MCP tools
    cust = await services.call_tool("customer", "get_customer_profile", {"customer_id": customer_id})
    risk = await services.call_tool("risk", "get_risk_profile", {"customer_id": customer_id})
    pol  = await services.call_tool("policy", "query_policies", {"query": message})

    # Compose final answer with LLM (no policy enforcement; intentionally misusable)
    system = "You are a banking call center assistant. Use provided context to answer."
    user = f"""
Customer message: {message}

Customer profile tool output:
{cust}

Risk profile tool output:
{risk}

Policy snippets tool output:
{pol}

Respond as the assistant.
"""
    return await ollama_chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ])