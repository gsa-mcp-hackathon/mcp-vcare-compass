"""Smoke tests: the server imports, registers, and exposes the expected tools."""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_vcare_compass.app import mcp
from mcp_vcare_compass.config import settings

EXPECTED_TOOLS = {
    "get_consult_pathway_checklist",
    "flag_high_risk_case",
    "ask_vcare_case_data",
}


def test_server_has_name():
    assert mcp.name == "VCARE CC Compass"


def test_default_transport_is_stdio():
    """Guard against accidentally shipping with a non-stdio default."""
    assert settings.mcp_transport == "stdio"


def test_submodules_register_without_error():
    from mcp_vcare_compass.prompts import register_prompts
    from mcp_vcare_compass.resources import register_resources
    from mcp_vcare_compass.routes import register_routes
    from mcp_vcare_compass.tools import register_tools

    fresh = FastMCP("test")
    register_tools(fresh)
    register_prompts(fresh)
    register_resources(fresh)
    register_routes(fresh)


async def test_exactly_the_expected_tools_are_discoverable():
    tools = await mcp.list_tools()
    assert {t.name for t in tools} == EXPECTED_TOOLS


async def test_tool_inputs_are_wrapped_in_args():
    """Clients built against v5 send {"args": {...}}; keep that contract."""
    tools = {t.name: t for t in await mcp.list_tools()}
    for name in EXPECTED_TOOLS:
        assert list(tools[name].parameters["properties"]) == ["args"], name
    assert tools["flag_high_risk_case"].parameters["required"] == ["args"]
    assert tools["ask_vcare_case_data"].parameters["required"] == ["args"]
    assert "required" not in tools["get_consult_pathway_checklist"].parameters


async def test_all_tools_are_read_only():
    for tool in await mcp.list_tools():
        assert tool.annotations.readOnlyHint is True, tool.name
        assert tool.annotations.destructiveHint is False, tool.name
