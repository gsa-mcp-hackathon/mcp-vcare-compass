"""Tests for the flag_high_risk_case screening rules.

All dates are relative to AS_OF (a Friday) so business-day math is predictable.
"""

from __future__ import annotations

from datetime import date

import pytest

from mcp_vcare_compass.models import FlagCaseInput
from mcp_vcare_compass.notices import FLAG_BOUNDARY_NOTICE
from mcp_vcare_compass.rules import business_days_between, screen_case

AS_OF = date(2026, 10, 30)  # Friday


def make_case(**overrides) -> FlagCaseInput:
    base = {
        "case_id": "TEST-0001",
        "category_of_care": "Radiology",
        "as_of": AS_OF,
        "coordination_level": "Basic",
        "consult_status": "Active",
    }
    base.update(overrides)
    return FlagCaseInput(**base)


def codes(case: FlagCaseInput) -> list[str]:
    return [f.code for f in screen_case(case).flags]


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 10, 23), date(2026, 10, 30), 5),  # Fri -> Fri
        (date(2026, 10, 24), date(2026, 10, 26), 1),  # Sat -> Mon
        (date(2026, 10, 30), date(2026, 10, 30), 0),
        (date(2026, 10, 30), date(2026, 10, 29), 0),  # end before start
    ],
)
def test_business_days_between(start, end, expected):
    assert business_days_between(start, end) == expected


def test_clean_case_is_not_flagged():
    out = screen_case(make_case())
    assert out.flagged is False
    assert out.flags == []
    assert out.boundary == FLAG_BOUNDARY_NOTICE
    assert out.thresholds_used == {
        "rfs_decision_business_days": 3,
        "no_action_days_high_risk": 30,
        "no_action_days_urgent_complex": 3,
    }


# ── Flag 1: RFS ───────────────────────────────────────────────────────────────────────
AUTHORIZED = {
    "authorized_date": date(2026, 10, 1),
    "care_initiated_date": date(2026, 10, 5),
}


def test_rfs_without_decision_past_clock():
    out = screen_case(make_case(rfs_complete_date=date(2026, 10, 23), **AUTHORIZED))
    assert [f.code for f in out.flags] == ["RFS_CLOCK"]
    assert out.flags[0].severity == "High"
    assert out.flags[0].finding == (
        "No RFS decision 5 business days after a complete submission (limit 3)."
    )


def test_rfs_decided_late():
    case = make_case(
        rfs_complete_date=date(2026, 10, 19),
        rfs_decision_date=date(2026, 10, 26),
        rfs_letter_date=date(2026, 10, 26),
        **AUTHORIZED,
    )
    out = screen_case(case)
    assert [f.code for f in out.flags] == ["RFS_CLOCK"]
    assert out.flags[0].finding == "RFS decided in 5 business days (limit 3)."


def test_rfs_within_clock_is_not_flagged():
    case = make_case(
        rfs_complete_date=date(2026, 10, 27),
        rfs_decision_date=date(2026, 10, 28),
        rfs_letter_date=date(2026, 10, 28),
        **AUTHORIZED,
    )
    assert codes(case) == []


def test_rfs_before_care_initiated_is_out_of_sequence():
    case = make_case(
        rfs_complete_date=date(2026, 10, 2),
        rfs_decision_date=date(2026, 10, 2),
        rfs_letter_date=date(2026, 10, 2),
        **AUTHORIZED,
    )
    out = screen_case(case)
    assert [f.code for f in out.flags] == ["RFS_SEQUENCE"]
    assert out.flags[0].severity == "Review"


def test_rfs_missing_authorization_dates_is_out_of_sequence():
    case = make_case(
        rfs_complete_date=date(2026, 10, 29), rfs_decision_date=date(2026, 10, 29)
    )
    assert codes(case) == ["RFS_SEQUENCE"]


def test_rfs_decision_without_letter():
    case = make_case(
        rfs_complete_date=date(2026, 10, 23),
        rfs_decision_date=date(2026, 10, 26),
        **AUTHORIZED,
    )
    assert codes(case) == ["RFS_LETTER"]


# ── Flags 2 and 4: coordination and no action ──────────────────────────────
def test_urgent_case_cancelled():
    case = make_case(coordination_level="Urgent", consult_status="Cancelled")
    out = screen_case(case)
    assert [f.code for f in out.flags] == ["COORD_CANCELLED"]
    assert out.flags[0].finding == "Urgent coordination case was cancelled."


def test_complex_case_idle_past_coordination_threshold_only():
    case = make_case(
        coordination_level="Complex/Chronic",
        last_nurse_action_date=date(2026, 10, 20),
    )
    out = screen_case(case)
    assert [f.code for f in out.flags] == ["COORD_TIMELINESS"]
    assert out.flags[0].finding == (
        "Complex/Chronic coordination case with 10 days since the last nurse "
        "action (threshold 3 days)."
    )


def test_urgent_case_idle_past_both_thresholds():
    case = make_case(
        coordination_level="Urgent", last_nurse_action_date=date(2026, 9, 1)
    )
    out = screen_case(case)
    assert [f.code for f in out.flags] == ["COORD_TIMELINESS", "NO_ACTION_LONG"]
    assert out.flags[1].severity == "Critical"
    assert out.flags[1].finding == (
        "Urgent case with 59 days with no action (threshold 30 days)."
    )


def test_oncology_override_tightens_coordination_threshold():
    idle_3_days = {
        "coordination_level": "Urgent",
        "last_nurse_action_date": date(2026, 10, 27),
    }
    oncology = screen_case(make_case(category_of_care="Oncology", **idle_3_days))
    assert [f.code for f in oncology.flags] == ["COORD_TIMELINESS"]
    assert oncology.thresholds_used["no_action_days_urgent_complex"] == 2
    assert codes(make_case(**idle_3_days)) == []


def test_high_risk_marker_without_any_action():
    out = screen_case(make_case(high_risk=True))
    assert [f.code for f in out.flags] == ["NO_ACTION_LONG"]
    assert out.flags[0].finding == (
        "Basic (High Risk) case with no documented action (threshold 30 days)."
    )


def test_basic_and_moderate_without_marker_are_not_no_action_flagged():
    for level in ("Basic", "Moderate"):
        assert codes(make_case(coordination_level=level)) == [], level


# ── Flag 3: death reported ────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("status", "related", "expected"),
    [
        ("Complete", None, ["DEATH_REPORTED"]),
        ("Cancelled", True, ["DEATH_REPORTED"]),
        ("Complete", False, []),
        ("Active", True, ["DEATH_REPORTED"]),
        ("Active", False, []),
    ],
)
def test_death_reported(status, related, expected):
    case = make_case(
        consult_status=status,
        death_reported=True,
        death_related_to_authorized_care=related,
    )
    assert codes(case) == expected


def test_death_finding_wording():
    case = make_case(consult_status="Complete", death_reported=True)
    finding = screen_case(case).flags[0].finding
    assert finding == (
        "Death reported; relationship undetermined for authorized care; "
        "consult complete."
    )


# ── Flag 5: Best Medical Interest ─────────────────────────────────────────
BMI_OK = {"bmi_eligibility": True, "bmi_agreement_documented": True}


def test_compliant_bmi_case_is_not_flagged():
    assert codes(make_case(**BMI_OK)) == []


def test_bmi_rules_ignored_when_not_a_bmi_case():
    case = make_case(
        bmi_second_review_documented=True,
        service_type="IVF",
        consult_status="Cancelled",
    )
    assert codes(case) == []


@pytest.mark.parametrize(
    ("determined", "expected"),
    [
        (date(2025, 6, 1), ["BMI_SECOND_REVIEW"]),
        (date(2025, 5, 19), ["BMI_SECOND_REVIEW"]),
        (None, ["BMI_SECOND_REVIEW"]),
        (date(2025, 1, 1), []),
    ],
)
def test_bmi_second_review_after_dole_act(determined, expected):
    case = make_case(
        bmi_second_review_documented=True, bmi_determination_date=determined, **BMI_OK
    )
    assert codes(case) == expected


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (" Veteran Declined ", []),
        (None, ["BMI_CANCEL_REASON"]),
        ("   ", ["BMI_CANCEL_REASON"]),
        ("cost", ["BMI_CANCEL_REASON"]),
    ],
)
def test_bmi_cancel_reason(reason, expected):
    case = make_case(consult_status="Cancelled", bmi_cancel_reason=reason, **BMI_OK)
    assert codes(case) == expected


def test_bmi_without_documented_agreement():
    for agreement in (None, False):
        case = make_case(bmi_eligibility=True, bmi_agreement_documented=agreement)
        assert codes(case) == ["BMI_NO_AGREEMENT"]


def test_bmi_for_excluded_service():
    out = screen_case(make_case(service_type="IVF consult", **BMI_OK))
    assert [f.code for f in out.flags] == ["BMI_EXCLUDED_SERVICE"]
    assert codes(make_case(service_type="MRI", **BMI_OK)) == []
