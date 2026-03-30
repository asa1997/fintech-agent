from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .intent_classifier import classify_intent

ESCALATION_TEXT = "This issue requires further investigation. I’m escalating this to our support team."

# 1. Define Pydantic Schemas for Strict Typing
class BalanceInput(BaseModel):
    account_id: str = Field(description="The ID of the account to check.")

class TransferInput(BaseModel):
    source_id: str = Field(description="The account ID to pull money from.")
    target_id: str = Field(description="The account ID to send money to.")
    amount: float = Field(description="The amount of money to transfer.")

class ProfileInput(BaseModel):
    customer_id: str = Field(description="The ID of the customer.")

async def handle_message(services, customer_id: str, message: str) -> str:
    # Fast path for complaints remains the same
    intent = await classify_intent(message)
    if intent == "complaint":
        return ESCALATION_TEXT

    # 2. Define LangChain Tools (Closing over `services` and `customer_id`)
    async def _get_balance(account_id: str) -> str:
        if account_id != customer_id:
            return "Security Violation: Unauthorized account access."
        try:
            res = await services.call_tool("banking", "get_balance", {"account_id": account_id})
            return str(res.content[0].text if hasattr(res, 'content') else res)
        except Exception as e:
            return f"Error: {str(e)}"

    async def _transfer_funds(source_id: str, target_id: str, amount: float) -> str:
        if source_id != customer_id:
            return "Security Violation: You can only transfer funds from your own account."
        try:
            res = await services.call_tool("banking", "transfer_funds", {"source_id": source_id, "target_id": target_id, "amount": amount})
            return str(res.content[0].text if hasattr(res, 'content') else res)
        except Exception as e:
            return f"Error: {str(e)}"

    async def _get_profile(customer_id_input: str) -> str:
        if customer_id_input != customer_id:
            return "Security Violation: Unauthorized profile access."
        try:
            res = await services.call_tool("customer", "get_customer_profile", {"customer_id": customer_id_input})
            return str(res.content[0].text if hasattr(res, 'content') else res)
        except Exception as e:
            return f"Error: {str(e)}"

    # Wrap functions into LangChain StructuredTools
    tools = [
        StructuredTool.from_function(
            coroutine=_get_balance,
            name="get_balance",
            description="Fetch the current balance for a specific account ID.",
            args_schema=BalanceInput,
        ),
        StructuredTool.from_function(
            coroutine=_transfer_funds,
            name="transfer_funds",
            description="Transfer funds from one account to another.",
            args_schema=TransferInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_profile,
            name="get_customer_profile",
            description="Get the banking profile for the current customer.",
            args_schema=ProfileInput,
        )
    ]

    # 3. Initialize the LLM (Must support tool calling, e.g., llama3.1)
    llm = ChatOllama(model="llama3.1", temperature=0)

    # 4. Create the Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an autonomous, secure banking assistant. Use the provided tools to help the user. The authenticated customer_id is {customer_id}."),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 5. Build and Execute the Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=5)

    # Run the chain
    response = await agent_executor.ainvoke({
        "input": message,
        "customer_id": customer_id
    })

    return response.get("output", "System Error.")