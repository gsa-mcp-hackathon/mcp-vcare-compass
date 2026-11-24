"""flag_high_risk_case — screen one synthetic consult case for review flags."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from mcp_vcare_compass.models import FlagCaseInput
from mcp_vcare_compass.rules import screen_case


def register(mcp: FastMCP) -> None:
    """Register flag_high_risk_case with the MCP server."""

    @mcp.tool(
        name="flag_high_risk_case",
        annotations={
            "title": "Flag High-Risk Case",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def flag_high_risk_case(args: FlagCaseInput) -> dict[str, Any]:
        """Screen ONE synthetic Community Care consult case and return any timeliness
        or patient-safety flags that suggest a Veteran may need prompt human
        follow-up. Checks five configurable rules: (1) RFS decision and letter
        within 3 business days of a complete submission (an RFS applies only after
        care is authorized and initiated); (2) Urgent or Complex/Chronic
        coordination cases that are cancelled or lack nurse follow-up; (3) a
        reported death on a consult of any status related to, or not ruled
        out from, authorized care; (4) Urgent, Complex/Chronic, or High Risk marked
        active cases with no action beyond the threshold (default 30 days); (5)
        Best Medical Interest (BMI) cases showing policy noncompliance: a second
        review after it was removed, cancellation without an accepted reason, no
        documented Veteran and clinician agreement, or BMI used for a service that
        other law excludes. Coordination level is Basic, Moderate, Complex/Chronic,
        or Urgent; High Risk is a separate true/false marker. Thresholds vary by
        category_of_care and seoc via configuration. Read-only. Returns flags,
        severity, and suggested next steps; it is a prototype screen, not a
        clinical determination."""
        return screen_case(args).model_dump(mode="json")
