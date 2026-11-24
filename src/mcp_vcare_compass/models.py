"""Pydantic models and enums: the typed contract for every tool's input/output.

Typed parameters give MCP clients a precise schema, which helps the LLM call
the tools correctly. Field descriptions are part of that contract — keep them
accurate when the rules change.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from mcp_vcare_compass.notices import CASE_DATA_BOUNDARY_NOTICE


# ── get_consult_pathway_checklist ─────────────────────────────────────────────────────
class PathwayStep(str, Enum):
    receive = "receive"
    triage = "triage"
    eligibility = "eligibility"
    authorize = "authorize"
    schedule = "schedule"
    follow_up = "follow_up"
    close = "close"


class PathwayChecklistInput(BaseModel):
    """Input for get_consult_pathway_checklist. Omit pathway_step for the full pathway."""  # noqa: E501

    pathway_step: PathwayStep | None = Field(
        None,
        description=(
            "One pathway step to retrieve. Omit to return the full 7-step pathway."
        ),
    )


class PathwayStepChecklist(BaseModel):
    step: str
    label: str
    description: str
    gemba_questions: list[str]
    sources: list[str]


class PathwayChecklistOutput(BaseModel):
    steps: list[PathwayStepChecklist]
    boundary: str
    last_reviewed: str


# ── flag_high_risk_case ───────────────────────────────────────────────────────────────
class CoordinationLevel(str, Enum):
    basic = "Basic"
    moderate = "Moderate"
    complex = "Complex/Chronic"
    urgent = "Urgent"


class ConsultStatus(str, Enum):
    active = "Active"
    complete = "Complete"
    cancelled = "Cancelled"


class FlagSeverity(str, Enum):
    critical = "Critical"
    high = "High"
    review = "Review"


class FlagCaseInput(BaseModel):
    """Input for flag_high_risk_case: one synthetic consult case. Use synthetic IDs only."""  # noqa: E501

    case_id: str = Field(
        description="Synthetic case identifier. Never a real patient identifier."
    )
    category_of_care: str = Field(
        description=(
            "Category of care, e.g. Radiology, Oncology, Acupuncture, Emergency Care."
        )
    )
    seoc: str | None = Field(
        None, description="Standardized Episode of Care, if applicable."
    )
    as_of: date = Field(
        description="Review date (YYYY-MM-DD) used for all clock calculations."
    )
    coordination_level: CoordinationLevel = Field(
        description=(
            "Care Coordination Model level: Basic, Moderate, Complex/Chronic, "
            "or Urgent."
        )
    )
    high_risk: bool = Field(
        False,
        description=(
            "True if the case carries a separate High Risk marker. "
            "Not a coordination level."
        ),
    )
    consult_status: ConsultStatus = Field(description="Current consult status.")
    authorized_date: date | None = Field(
        None, description="Date community care was authorized (YYYY-MM-DD)."
    )
    care_initiated_date: date | None = Field(
        None, description="Date community care was initiated (YYYY-MM-DD)."
    )
    last_nurse_action_date: date | None = Field(
        None,
        description=(
            "Most recent documented nurse follow-up or care coordination action."
        ),
    )
    rfs_complete_date: date | None = Field(
        None, description="Date a complete Request for Services was received."
    )
    rfs_decision_date: date | None = Field(
        None, description="Date the RFS decision was documented."
    )
    rfs_letter_date: date | None = Field(
        None, description="Date the RFS decision letter was issued."
    )
    death_reported: bool = Field(
        False, description="True if a death is reported in the source record."
    )
    death_related_to_authorized_care: bool | None = Field(
        None, description="Per the source record. Omit if undetermined."
    )
    # Best Medical Interest (BMI) fields — leave at defaults for non-BMI cases.
    bmi_eligibility: bool = Field(
        False,
        description=(
            "True if the community care eligibility reason is Best Medical Interest."
        ),
    )
    bmi_determination_date: date | None = Field(
        None,
        description="Date the BMI determination was documented (YYYY-MM-DD).",
    )
    bmi_agreement_documented: bool | None = Field(
        None,
        description=(
            "True if joint Veteran and referring clinician agreement is documented."
        ),
    )
    bmi_second_review_documented: bool | None = Field(
        None,
        description=(
            "True if a second clinical review of the BMI determination is documented."
        ),
    )
    bmi_cancel_reason: str | None = Field(
        None,
        description=(
            "Cancellation reason recorded on a cancelled BMI consult. "
            "Omit if none recorded."
        ),
    )
    service_type: str | None = Field(
        None,
        description=(
            "Service requested (e.g. dental, IVF, transplant), used for the BMI "
            "other-law exclusion check."
        ),
    )


class FlagFinding(BaseModel):
    code: str
    severity: FlagSeverity
    finding: str
    next_step: str


class FlagCaseOutput(BaseModel):
    case_id: str
    flagged: bool
    flags: list[FlagFinding]
    thresholds_used: dict[str, int]
    boundary: str


# ── ask_vcare_case_data ───────────────────────────────────────────────────────────────
class AskCaseDataInput(BaseModel):
    """Input for ask_vcare_case_data."""

    question: str = Field(
        description="Natural-language question about the synthetic consult case data."
    )
    conversation_id: str | None = Field(
        None,
        description=(
            "conversation_id from a previous answer, to ask a follow-up in context. "
            "Omit to start a new conversation."
        ),
    )


class AskCaseDataOutput(BaseModel):
    status: str
    answer: str | None = None
    sql: str | None = None
    columns: list[str] = []
    rows: list[list[str | None]] = []
    total_row_count: int | None = None
    rows_truncated: bool = False
    suggested_questions: list[str] = []
    conversation_id: str | None = None
    error: str | None = None
    boundary: str = CASE_DATA_BOUNDARY_NOTICE
