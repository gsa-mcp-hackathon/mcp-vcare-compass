"""Standardized GEMBA consult pathway: observation questions and policy citations.

Public/policy content only. Each step lists what a reviewer should observe and
the authoritative sources behind it. Update LAST_REVIEWED whenever the
questions or sources change.
"""

from __future__ import annotations

from datetime import date

from mcp_vcare_compass.models import (
    PathwayChecklistInput,
    PathwayChecklistOutput,
    PathwayStepChecklist,
)
from mcp_vcare_compass.notices import BOUNDARY_NOTICE

LAST_REVIEWED = date(2026, 10, 1)

AUTHORITATIVE_SOURCES = {
    "ccm_101": "CCM 101 (Community Care Manual, consult lifecycle)",
    "ivc_process_flow": "IVC Care Coordination Process Flow",
    "rfs_sop": "RFS SOP (Request for Service Standard Operating Procedure)",
    "vha_1230": "VHA Directive 1230",
    "vha_1232": "VHA Directive 1232",
    "mission_act": "Public Law 115-182 (VA MISSION Act of 2018)",
    "dole_act": "Public Law 118-210 (Dole Act) — BMI review-step change",
}

CONSULT_PATHWAY = {
    "receive": {
        "label": "Receive",
        "description": "Consult is entered into the system and initially logged.",
        "gemba_questions": [
            "Is the consult logged in the system of record within the expected timeframe of receipt?",
            "Is the reason for request and referring provider clearly documented?",
            "Is the consult routed to the correct service/queue on first entry?",
        ],
        "sources": [
            AUTHORITATIVE_SOURCES["ccm_101"],
            AUTHORITATIVE_SOURCES["ivc_process_flow"],
        ],
    },
    "triage": {
        "label": "Triage",
        "description": "Consult is reviewed and assigned a priority/complexity level.",
        "gemba_questions": [
            "Is a triage or complexity level assigned, and is the basis for that level documented?",
            "Is there evidence the triage step happened within the expected window?",
            "For high-complexity cases, is there a documented escalation path?",
        ],
        "sources": [AUTHORITATIVE_SOURCES["ivc_process_flow"]],
    },
    "eligibility": {
        "label": "Eligibility",
        "description": "Community care eligibility criteria are assessed against MISSION Act pathways.",
        "gemba_questions": [
            "Is the eligibility pathway (wait time, drive time, service unavailable, best medical interest) documented?",
            "If best medical interest is the pathway, is the Dole Act's streamlined review step reflected (no extra, now-removed review)?",
            "Is the eligibility determination traceable to a specific standard, not just a note that 'CC applies'?",
        ],
        "sources": [
            AUTHORITATIVE_SOURCES["mission_act"],
            AUTHORITATIVE_SOURCES["dole_act"],
            AUTHORITATIVE_SOURCES["ccm_101"],
        ],
    },
    "authorize": {
        "label": "Authorize",
        "description": "Clinical/administrative authorization is granted before community care proceeds.",
        "gemba_questions": [
            "Is there a documented authorization decision prior to the Veteran receiving community care?",
            "Is the authorizing role/reviewer identified?",
            "Is there a documented clinical review where one is required for the pathway used?",
        ],
        "sources": [
            AUTHORITATIVE_SOURCES["vha_1230"],
            AUTHORITATIVE_SOURCES["rfs_sop"],
        ],
    },
    "schedule": {
        "label": "Schedule",
        "description": "An appointment is secured with the community provider.",
        "gemba_questions": [
            "Is there a documented appointment date within the applicable access standard?",
            "Is there evidence of Veteran choice being offered/discussed where applicable?",
            "If scheduling is delayed, is the delay reason documented?",
        ],
        "sources": [
            AUTHORITATIVE_SOURCES["rfs_sop"],
            AUTHORITATIVE_SOURCES["mission_act"],
        ],
    },
    "follow_up": {
        "label": "Follow-up",
        "description": "Care coordination continues at a cadence appropriate to risk/complexity.",
        "gemba_questions": [
            "Is there a documented care-coordination note or CC-CCP update appropriate to the case complexity?",
            "For aged consults, is there documented outreach consistent with the expected cadence?",
            "Is responsibility for follow-up assigned to a named role?",
        ],
        "sources": [
            AUTHORITATIVE_SOURCES["vha_1232"],
            AUTHORITATIVE_SOURCES["ivc_process_flow"],
        ],
    },
    "close": {
        "label": "Close",
        "description": "The consult episode is completed and documented as closed.",
        "gemba_questions": [
            "Is there a documented closure action (e.g., results received, episode completed)?",
            "Is the reason for closure clear (completed, Veteran declined, administratively closed)?",
            "Is there anything in the closure record suggesting the Veteran needs continued follow-up?",
        ],
        "sources": [
            AUTHORITATIVE_SOURCES["ccm_101"],
            AUTHORITATIVE_SOURCES["vha_1232"],
        ],
    },
}


def get_pathway_checklist(args: PathwayChecklistInput) -> PathwayChecklistOutput:
    """Return the GEMBA checklist for one pathway step, or the full pathway."""
    if args.pathway_step is not None:
        key = args.pathway_step.value
        steps_to_return = {key: CONSULT_PATHWAY[key]}
    else:
        steps_to_return = CONSULT_PATHWAY

    steps = [
        PathwayStepChecklist(
            step=key,
            label=val["label"],
            description=val["description"],
            gemba_questions=val["gemba_questions"],
            sources=val["sources"],
        )
        for key, val in steps_to_return.items()
    ]

    return PathwayChecklistOutput(
        steps=steps,
        boundary=BOUNDARY_NOTICE,
        last_reviewed=LAST_REVIEWED.isoformat(),
    )
