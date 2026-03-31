from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from agent.mcp_client import MCPServices
from agent.agent import handle_message

# Initialize services globally so the lifespan and endpoints can access it
services = MCPServices()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    print("Initializing MCP Servers...")
    await services.start()
    
    yield # This yields control back to FastAPI so it can serve requests
    
    # --- Shutdown Logic ---
    print("Shutting down MCP Servers...")
    await services.close()

# Pass the lifespan function into the FastAPI app initialization
app = FastAPI(lifespan=lifespan)

class MessageRequest(BaseModel):
    customer_id: str
    message: str

@app.post("/chat")
async def chat(req: MessageRequest):
    # Pass the incoming API payload to your agent loop
    response = await handle_message(services, req.customer_id, req.message)
    return {"reply": response}

if __name__ == "__main__":
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)