"""HTTP transport tests: what the Databricks Apps proxy will see."""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from mcp_vcare_compass import __version__
from mcp_vcare_compass.app import HTTP_OPTIONS, mcp

# A Databricks Apps host name: the proxy forwards requests with this Host.
APP_HOST = "vcare-pathway-checklist-7474654188777746.aws.databricksapps.com"
MCP_HEADERS = {
    "Host": APP_HOST,
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


@pytest.fixture
def http():
    with TestClient(mcp.http_app(**HTTP_OPTIONS)) as c:
        yield c


def rpc(http, method, params, rpc_id=1):
    body = {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}
    resp = http.post("/mcp", headers=MCP_HEADERS, content=json.dumps(body))
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/json")
    return resp.json()


def test_health_and_version(http):
    assert http.get("/health").json() == {
        "status": "healthy",
        "service": "mcp-vcare-compass",
    }
    assert http.get("/version").json() == {"version": __version__}


def test_landing_page_lists_tools(http):
    text = http.get("/").text
    assert "VCARE CC Compass MCP server is running" in text
    assert "ask_vcare_case_data" in text


def test_stateless_tools_list_behind_proxy_host(http):
    """No initialize handshake or session ID needed (stateless HTTP)."""
    result = rpc(http, "tools/list", {})["result"]
    assert {t["name"] for t in result["tools"]} == {
        "get_consult_pathway_checklist",
        "flag_high_risk_case",
        "ask_vcare_case_data",
    }


def test_tools_call_over_http(http):
    result = rpc(
        http,
        "tools/call",
        {
            "name": "get_consult_pathway_checklist",
            "arguments": {"args": {"pathway_step": "triage"}},
        },
    )["result"]
    assert result.get("isError") is not True
    payload = json.loads(result["content"][0]["text"])
    assert [s["step"] for s in payload["steps"]] == ["triage"]
