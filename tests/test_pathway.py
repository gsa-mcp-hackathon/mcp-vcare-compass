"""Tests for the GEMBA consult-pathway checklist."""

from __future__ import annotations

from mcp_vcare_compass.models import PathwayChecklistInput, PathwayStep
from mcp_vcare_compass.notices import BOUNDARY_NOTICE
from mcp_vcare_compass.pathway import get_pathway_checklist

STEP_ORDER = [
    "receive",
    "triage",
    "eligibility",
    "authorize",
    "schedule",
    "follow_up",
    "close",
]


def test_full_pathway_has_seven_steps_in_order():
    out = get_pathway_checklist(PathwayChecklistInput())
    assert [s.step for s in out.steps] == STEP_ORDER
    assert out.boundary == BOUNDARY_NOTICE
    assert out.last_reviewed == "2026-10-01"


def test_every_step_has_questions_and_sources():
    for step in get_pathway_checklist(PathwayChecklistInput()).steps:
        assert len(step.gemba_questions) == 3, step.step
        assert step.sources, step.step


def test_single_step_is_scoped():
    out = get_pathway_checklist(
        PathwayChecklistInput(pathway_step=PathwayStep.eligibility)
    )
    assert [s.step for s in out.steps] == ["eligibility"]
    assert out.steps[0].label == "Eligibility"
    assert any("Dole Act" in src for src in out.steps[0].sources)
