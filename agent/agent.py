import json
from .intent_classifier import classify_intent
from .ollama_client import ollama_chat

ESCALATION_TEXT = "This issue requires further investigation. I’m escalating this to our support team."

# The Brain's Instructions
SYSTEM_PROMPT = """You are an autonomous, secure banking assistant. 
You have access to the following tools:
- get_balance: args: {"account_id": "<string>"}
- transfer_funds: args: {"source_id": "<string>", "target_id": "<string>", "amount": <float>}
- get_customer_profile: args: {"customer_id": "<string>"}

You must execute actions by outputting STRICTLY valid JSON without any markdown formatting. 
If you need to use a tool, output: 
{"action": "call_tool", "tool_name": "<name>", "arguments": {"arg1": "value"}}

If you have enough information to answer the user, output: 
{"action": "final_answer", "text": "<your response to the user>"}

Do not output any other text or explanations outside of the JSON block.
"""

async def handle_message(services, customer_id: str, message: str) -> str:
    # 1. Fast path for complaints
    intent = await classify_intent(message)
    if intent == "complaint":
        return ESCALATION_TEXT

    # 2. Initialize the conversation state
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Authenticated Customer ID: {customer_id}\nUser Message: {message}"}
    ]

    # 3. The Execution Loop (Capped at 5 to prevent infinite loops/hallucinations)
    for step in range(5):
        # Ask the LLM what to do next
        raw_response = await ollama_chat(messages)
        
        try:
            # Strip potential markdown code blocks the LLM might hallucinate
            clean_response = raw_response.replace("```json", "").replace("```", "").strip()
            decision = json.loads(clean_response)
        except json.JSONDecodeError:
            # If the LLM outputs garbage, feed the error back so it self-corrects
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "user", "content": "Error: You must output strictly valid JSON. Try again."})
            continue

        # Record the LLM's valid decision in the context
        messages.append({"role": "assistant", "content": clean_response})

        # Branch A: The LLM is done and wants to speak to the user
        if decision.get("action") == "final_answer":
            return decision.get("text", "Error: No text provided in final answer.")
            
        # Branch B: The LLM wants to use a tool
        elif decision.get("action") == "call_tool":
            tool_name = decision.get("tool_name")
            args = decision.get("arguments", {})
            
            # Map the tool to the correct MCP server
            service_map = {
                "get_balance": "banking",
                "transfer_funds": "banking",
                "get_customer_profile": "customer"
            }
            
            target_service = service_map.get(tool_name)
            
            if not target_service:
                tool_result = f"Error: Tool {tool_name} does not exist or is unauthorized."
            else:
                # Security Check: Prevent the LLM from querying other users' data
                # A real production system enforces this at the MCP server level, 
                # but we catch it here to prevent basic prompt injections.
                if tool_name in ["get_balance", "get_customer_profile"] and args.get("account_id", args.get("customer_id")) != customer_id:
                    tool_result = "Security Violation: You are not authorized to access other accounts."
                else:
                    # Execute the MCP tool
                    try:
                        mcp_result = await services.call_tool(target_service, tool_name, args)
                        # MCP returns a CallToolResult object, we extract the text
                        tool_result = str(mcp_result.content[0].text if mcp_result.content else mcp_result)
                    except Exception as e:
                        tool_result = f"Tool Execution Failed: {str(e)}"

            # Feed the physical result back to the LLM so it can observe what happened
            messages.append({"role": "user", "content": f"Tool Result: {tool_result}"})
            
    return "System Error: Agent exceeded maximum execution steps. Transaction aborted."