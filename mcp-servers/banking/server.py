import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Banking Service", json_response=True)

# Path to your dummy ledger
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "accounts.json"

def _load_accounts() -> dict:
    """Helper to read the JSON file."""
    if not DATA_PATH.exists():
        return {}
    return json.loads(DATA_PATH.read_text())

def _save_accounts(data: dict):
    """Helper to write back to the JSON file."""
    DATA_PATH.write_text(json.dumps(data, indent=2))

@mcp.tool()
def get_balance(account_id: str) -> dict:
    """Fetch the current balance for a specific account ID."""
    accounts = _load_accounts()
    
    if account_id not in accounts:
        return {"error": f"Account {account_id} not found."}
        
    return {"account_id": account_id, "data": accounts[account_id]}

@mcp.tool()
def transfer_funds(source_id: str, target_id: str, amount: float) -> dict:
    """Transfer funds from one account to another."""
    if amount <= 0:
        return {"error": "Transfer amount must be greater than zero."}

    accounts = _load_accounts()

    if source_id not in accounts:
        return {"error": f"Source account {source_id} not found."}
    if target_id not in accounts:
        return {"error": f"Target account {target_id} not found."}

    source_balance = accounts[source_id]["balance"]
    
    # Check for sufficient funds
    if source_balance < amount:
        return {
            "error": "Insufficient funds.",
            "current_balance": source_balance,
            "attempted_transfer": amount
        }

    # Execute the transfer in memory
    accounts[source_id]["balance"] -= amount
    accounts[target_id]["balance"] += amount

    # Commit to the JSON database
    _save_accounts(accounts)

    return {
        "status": "success",
        "message": f"Successfully transferred {amount} from {source_id} to {target_id}.",
        "new_source_balance": accounts[source_id]["balance"]
    }

if __name__ == "__main__":
    # Run the server via standard input/output
    mcp.run(transport="stdio")