from fastapi import FastAPI
from pydantic import BaseModel

from agent.mcp_client import MCPServices
from agent.agent import handle_message

app = FastAPI()
services = MCPServices()

class ChatIn(BaseModel):
    customer_id: str
    message: str

class ChatOut(BaseModel):
    response: str

@app.on_event("startup")
async def startup():
    await services.start()

@app.on_event("shutdown")
async def shutdown():
    await services.close()

@app.post("/chat", response_model=ChatOut)
async def chat(inp: ChatIn):
    resp = await handle_message(services, inp.customer_id, inp.message)
    return {"response": resp}