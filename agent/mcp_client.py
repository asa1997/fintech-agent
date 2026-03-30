import asyncio
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]

class MCPServices:
    def __init__(self):
        self.stack = AsyncExitStack()
        self.sessions = {}

    async def start(self):
        # Existing connections
        await self._connect("customer", ROOT / "mcp-servers" / "customer-profile" / "server.py")
        await self._connect("risk", ROOT / "mcp-servers" / "credit-risk" / "server.py")
        # await self._connect("policy", ROOT / "mcp-servers" / "rag-policy" / "server.py")
        await self._connect("banking", ROOT / "mcp-servers" / "banking" / "server.py")
        
        return self

    async def _connect(self, name: str, script_path: Path):
        params = StdioServerParameters(
            command="python",
            args=[str(script_path)],
            env=None
        )
        transport = await self.stack.enter_async_context(stdio_client(params))
        read, write = transport
        session = await self.stack.enter_async_context(ClientSession(read, write))
        await session.initialize()  # MCP handshake 
        self.sessions[name] = session

    async def call_tool(self, service: str, tool: str, arguments: dict):
        session = self.sessions[service]
        return await session.call_tool(tool, arguments=arguments)

    async def close(self):
        await self.stack.aclose()