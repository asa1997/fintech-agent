import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Credit & Risk Service", json_response=True)

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "risk.json"

@mcp.tool()
def get_risk_profile(customer_id: str) -> dict:
    """Return credit score, risk banding, and flags."""
    risk_db = json.loads(DATA_PATH.read_text())
    return risk_db.get(customer_id, {
        "credit_score": 650,
        "score_band": "medium",
        "fraud_risk": "low",
        "repayment_risk": "medium",
        "flags": []
    })

if __name__ == "__main__":
    mcp.run(transport="stdio")