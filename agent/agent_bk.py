import json
import re
import logging
from .intent_classifier import classify_intent
from .ollama_client import ollama_chat

logger = logging.getLogger(__name__)

ESCALATION_TEXT = "This issue requires further investigation. I’m escalating this to our support team."

# FIX: Added strict negative constraints and explicitly mentioned unsupported actions.
SYSTEM_PROMPT = """You are an autonomous banking assistant. 
You have access to the following tools AND NO OTHERS:
- get_balance: args: {"account_id": "<string>"}
- transfer_funds: args: {"source_id": "<string>", "target_id": "<string>", "amount": <float>}
- get_customer_profile: args: {"customer_id": "<string>"}

CRITICAL INSTRUCTIONS:
1. You must output EXACTLY ONE JSON object and NOTHING ELSE. Do not include markdown outside the JSON brackets.
2. If the user asks you to perform an action you do not have a tool for (like withdrawing funds, adding funds, or closing an account), DO NOT guess a tool name and DO NOT try to use a different tool. 
3. If you cannot fulfill the request, immediately output a "final_answer" politely explaining your limitations.

IF YOU NEED TO USE A TOOL, output exactly this format:
{"action": "call_tool", "tool_name": "get_balance", "arguments": {"account_id": "acc_123"}}

IF YOU HAVE THE FINAL ANSWER (or cannot perform the request), output exactly this format:
{"action": "final_answer", "text": "I cannot withdraw funds because I only have access to transfers and balance checks."}
"""

async def handle_message(services, customer_id: str, message: str) -> str:
    intent = await classify_intent(message)
    if intent == "complaint":
        logger.info("Intent classified as complaint. Escalating.")
        return ESCALATION_TEXT

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Authenticated Customer ID: {customer_id}\nUser Message: {message}"}
    ]

    logger.info(f"Starting agent loop for user message: '{message}'")

    for step in range(5):
        logger.info(f"--- [STEP {step + 1}] LLM is generating response ---")
        raw_response = await ollama_chat(messages)
        
        logger.debug(f"Raw LLM Output:\n{raw_response}")

        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        
        if not match:
            logger.warning("No JSON found in response. Forcing correction.")
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "user", "content": "Error: I could not find a valid JSON object in your response. Output ONLY JSON."})
            continue

        clean_json_string = match.group(0)

        try:
            decision = json.loads(clean_json_string)
            logger.debug(f"Parsed Decision: {decision}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parsing failed: {str(e)}. Forcing correction.")
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "user", "content": f"JSON Parsing Error: {str(e)}. Fix your JSON formatting and try again."})
            continue

        messages.append({"role": "assistant", "content": clean_json_string})

        if decision.get("action") == "final_answer":
            logger.info("Final Answer reached. Exiting loop.")
            return decision.get("text", "Error: No text provided in final answer.")
            
        elif decision.get("action") == "call_tool":
            tool_name = decision.get("tool_name")
            args = decision.get("arguments", {})
            
            logger.info(f"Executing tool: {tool_name} with args: {args}")
            
            service_map = {
                "get_balance": "banking",
                "transfer_funds": "banking",
                "get_customer_profile": "customer"
            }
            
            target_service = service_map.get(tool_name)
            
            if not target_service:
                tool_result = f"Error: Tool {tool_name} does not exist. Do not try to use it again. Tell the user you cannot perform this action."
                logger.error(tool_result)
            else:
                if tool_name in ["get_balance", "get_customer_profile"] and args.get("account_id", args.get("customer_id")) != customer_id:
                    tool_result = "Security Violation: You are not authorized to access other accounts."
                    logger.warning(f"Security block triggered: {tool_result}")
                else:
                    try:
                        mcp_result = await services.call_tool(target_service, tool_name, args)
                        tool_result = str(mcp_result.content[0].text if hasattr(mcp_result, 'content') and mcp_result.content else mcp_result)
                        logger.debug(f"MCP Server Response: {tool_result}")
                    except Exception as e:
                        tool_result = f"Tool Execution Failed: {str(e)}"
                        logger.error(tool_result)

            messages.append({"role": "user", "content": f"Tool Result: {tool_result}"})
            
    logger.error("Fatal Error: Max execution steps exceeded. Transaction aborted.")
    return "System Error: Agent exceeded maximum execution steps. Transaction aborted."