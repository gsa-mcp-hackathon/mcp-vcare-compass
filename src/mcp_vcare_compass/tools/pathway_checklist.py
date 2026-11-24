"""get_consult_pathway_checklist — standardized GEMBA consult-pathway checklist."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_vcare_compass.models import PathwayChecklistInput
from mcp_vcare_compass.pathway import get_pathway_checklist


def register(mcp: FastMCP) -> None:
    """Register get_consult_pathway_checklist with the MCP server."""

    @mcp.tool(
        name="get_consult_pathway_checklist",
        annotations={
            "title": "Consult Pathway Checklist",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def get_consult_pathway_checklist(
        args: PathwayChecklistInput | None = None,
    ) -> dict[str, Any]:
        """Return the standardized GEMBA consult-pathway checklist (receive, triage,
        eligibility, authorize, schedule, follow_up, close), cited to CC guidebooks
        and memoranda. Pass a single pathway_step to scope the result, or omit it
        for the full 7-step pathway. Explains what to observe at each step; does
        not score, certify, or determine anything about a specific consult."""
        return get_pathway_checklist(args or PathwayChecklistInput()).model_dump()
