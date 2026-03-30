import asyncio
import sys
from agent.mcp_client import MCPServices
from agent.agent import handle_message

async def main():
    print("Starting Banking Agent... (Initializing MCP Servers)")
    services = MCPServices()
    
    try:
        # Boot up all connected MCP servers (customer, risk, policy, banking)
        await services.start()
        print("\n✅ System Ready. Connected to MCP Servers.")
        print("Type 'exit' or 'quit' to stop.\n")
        
        # We hardcode the session ID to match the dummy database we created
        customer_id = "acc_123" 
        print(f"[Authenticated as {customer_id}]\n")

        # The interactive terminal loop
        while True:
            try:
                user_input = input("You: ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input.strip():
                    continue

                print("Agent is thinking...")
                # Pass the input to your custom ReAct loop
                response = await handle_message(services, customer_id, user_input)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                # Catch Ctrl+C to exit cleanly
                break
                
    finally:
        # Ensure all subprocesses are killed when exiting
        print("\nShutting down MCP servers...")
        await services.close()
        print("Offline.")

if __name__ == "__main__":
    asyncio.run(main())