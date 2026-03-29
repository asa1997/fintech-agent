import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Customer Profile Service", json_response=True)

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "customers.json"

@mcp.tool()
def get_customer_profile(customer_id: str) -> dict:
    """Return customer profile context."""
    customers = json.loads(DATA_PATH.read_text())
    return customers.get(customer_id, {"customer_id": customer_id, "segment": "standard"})

if __name__ == "__main__":
    # stdio is easiest for local orchestration with ClientSession 
    mcp.run(transport="stdio")