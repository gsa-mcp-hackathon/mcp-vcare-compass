"""ask_vcare_case_data — questions over the synthetic consult data via Genie."""

from __future__ import annotations

from typing import Any

from anyio import to_thread
from fastmcp import FastMCP

from mcp_vcare_compass.genie import ask_genie
from mcp_vcare_compass.models import AskCaseDataInput


def register(mcp: FastMCP) -> None:
    """Register ask_vcare_case_data with the MCP server."""

    @mcp.tool(
        name="ask_vcare_case_data",
        annotations={
            "title": "Ask VCARE Case Data",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def ask_vcare_case_data(args: AskCaseDataInput) -> dict[str, Any]:
        """Answer a natural-language question about the synthetic VA Community Care
        consult case data (600 fictitious consults) using the Genie agent
        "Healthcare Risk and Coordination Analysis". Covers case-level risk
        (high-risk = High_Risk_Flag Yes; risk level High/Moderate/Low; risk
        reasons), the three compliance pillars (timeliness, process, care
        coordination) and overall compliance flag, reviewer recommended actions,
        coordination level, category of care, consult dates, and facility-level
        breakdowns. Does NOT cover flag-code results, Best Medical Interest (BMI),
        RFS timelines, or death reporting; use flag_high_risk_case to screen a
        single case. Returns the answer text, the SQL that was run, up to 20 result
        rows, suggested follow-ups, and a conversation_id; pass conversation_id
        back to ask a follow-up in context. Read-only. Synthetic data only; results
        are administrative test priorities, not clinical determinations."""
        # The Genie SDK call blocks while it polls; run it off the event loop.
        result = await to_thread.run_sync(ask_genie, args)
        return result.model_dump(mode="json")
