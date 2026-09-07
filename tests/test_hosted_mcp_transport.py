"""Exercise the real public MCP transport, not just its static server card."""
import json
import pytest
from starlette.testclient import TestClient
from mcp_server import mcp

PUBLIC_HOST = "mcp-vibes-coded-production.up.railway.app"
HEADERS = {"Accept": "application/json, text/event-stream"}
INITIALIZE = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {},
               "clientInfo": {"name": "transport-regression", "version": "1.0"}},
}


@pytest.fixture(scope="module")
def client():
    # FastMCP session managers can only start once per server instance.
    with TestClient(mcp.streamable_http_app(), base_url=f"https://{PUBLIC_HOST}") as test_client:
        yield test_client


def _message(response):
    if "application/json" in response.headers.get("content-type", ""):
        return response.json()
    return json.loads(next(line[6:] for line in response.text.splitlines()
                           if line.startswith("data: ")))


def test_advertised_public_host_can_initialize_and_list_tools(client):
    response = client.post("/mcp", headers=HEADERS, json=INITIALIZE)
    assert response.status_code == 200, response.text
    assert "result" in _message(response)
    headers = {**HEADERS, "Mcp-Session-Id": response.headers["mcp-session-id"],
               "MCP-Protocol-Version": "2025-03-26"}
    response = client.post("/mcp", headers=headers, json={
        "jsonrpc": "2.0", "method": "notifications/initialized"})
    assert response.status_code == 202, response.text
    response = client.post("/mcp", headers=headers, json={
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert response.status_code == 200, response.text
    assert any(tool["name"] == "health" for tool in _message(response)["result"]["tools"])


def test_untrusted_host_is_still_rejected(client):
    response = client.post("/mcp", headers={**HEADERS, "Host": "untrusted.invalid"},
                           json=INITIALIZE)
    assert response.status_code == 421, response.text


def test_untrusted_browser_origin_is_still_rejected(client):
    response = client.post("/mcp", headers={**HEADERS, "Origin": "https://untrusted.invalid"},
                           json=INITIALIZE)
    assert response.status_code == 403, response.text
