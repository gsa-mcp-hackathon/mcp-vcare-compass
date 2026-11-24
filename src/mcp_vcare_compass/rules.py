"""Screening rules for flag_high_risk_case.

Thresholds live in FLAG_CONFIG, not in the logic. "overrides" are keyed by
(category_of_care, seoc); seoc None = any SEOC in that category. A
(category, seoc) entry beats a (category, None) entry.

Read-only: screen_case returns findings for human review, never a determination.
"""

from __future__ import annotations

from datetime import date, timedelta

from mcp_vcare_compass.models import (
    ConsultStatus,
    CoordinationLevel,
    FlagCaseInput,
    FlagCaseOutput,
    FlagFinding,
    FlagSeverity,
)
from mcp_vcare_compass.notices import FLAG_BOUNDARY_NOTICE

FLAG_CONFIG = {
    "defaults": {
        # RFS decision due within 3 business days of a complete submission
        "rfs_decision_business_days": 3,
        # High Risk / Urgent / Complex: no action beyond this = flag
        "no_action_days_high_risk": 30,
        # PLACEHOLDER — Urgent/Complex nurse follow-up; confirm with owner
        "no_action_days_urgent_complex": 3,
    },
    # Best Medical Interest (BMI) policy settings. Public basis: 38 CFR
    # 17.4010(a)(5); Dole Act (Public Law 118-210) removed the second VA
    # physician review, announced 2025-05-19.
    "bmi": {
        "second_review_removed_on": date(2025, 5, 19),
        # PLACEHOLDER list of acceptable BMI cancellation reasons. Replace with the
        # exact reasons from the BMI guideline before any evaluation run.
        # Matching is case-insensitive.
        "allowed_cancel_reasons": [
            "veteran declined",
            "veteran request",
            "care no longer needed",
            "duplicate consult",
            "entered in error",
            "veteran deceased",
        ],
        # Services a BMI determination may not override (other law-based
        # eligibility criteria).
        "excluded_services": [
            "ivf",
            "dental",
            "transplant",
            "homemaker/home health aide",
            "respite",
            "nursing home",
            "mental health residential",
            "rehabilitation treatment program",
        ],
    },
    "overrides": {
        # illustrative example only
        ("Oncology", None): {"no_action_days_urgent_complex": 2},
    },
}


def business_days_between(start: date, end: date) -> int:
    """Business days after `start` up to and including `end`.

    Weekends are skipped; federal holidays are not modeled.
    """
    count, day = 0, start
    while day < end:
        day += timedelta(days=1)
        if day.weekday() < 5:
            count += 1
    return count


def thresholds_for(case: FlagCaseInput) -> dict[str, int]:
    """Defaults, then category-wide override, then category+SEOC override."""
    rules = dict(FLAG_CONFIG["defaults"])
    rules.update(FLAG_CONFIG["overrides"].get((case.category_of_care, None), {}))
    if case.seoc:
        rules.update(
            FLAG_CONFIG["overrides"].get((case.category_of_care, case.seoc), {})
        )
    return rules


def screen_case(case: FlagCaseInput) -> FlagCaseOutput:
    """Apply the configured flags to one case."""
    rules = thresholds_for(case)
    flags: list[FlagFinding] = []
    idle_days = (
        (case.as_of - case.last_nurse_action_date).days
        if case.last_nurse_action_date
        else None
    )
    urgent_or_complex = case.coordination_level in (
        CoordinationLevel.urgent,
        CoordinationLevel.complex,
    )

    # Flag 1 — RFS 3-business-day clock (an RFS applies only after care is
    # authorized and initiated)
    if case.rfs_complete_date:
        if (
            not (case.authorized_date and case.care_initiated_date)
            or case.rfs_complete_date < case.care_initiated_date
        ):
            flags.append(
                FlagFinding(
                    code="RFS_SEQUENCE",
                    severity=FlagSeverity.review,
                    finding=(
                        "RFS is dated before community care was authorized and "
                        "initiated, or those dates are missing."
                    ),
                    next_step=(
                        "Verify the dates in the record; an RFS applies only after "
                        "community care is authorized and initiated."
                    ),
                )
            )
        limit = rules["rfs_decision_business_days"]
        end = case.rfs_decision_date or case.as_of
        used = business_days_between(case.rfs_complete_date, end)
        if used > limit:
            if case.rfs_decision_date:
                text = f"RFS decided in {used} business days (limit {limit})."
                step = "Review the cause of the processing delay with the site."
            else:
                text = (
                    f"No RFS decision {used} business days after a complete "
                    f"submission (limit {limit})."
                )
                step = "Escalate to the Delegate of Authority for a decision."
            flags.append(
                FlagFinding(
                    code="RFS_CLOCK",
                    severity=FlagSeverity.high,
                    finding=text,
                    next_step=step,
                )
            )
        if (
            case.rfs_decision_date
            and not case.rfs_letter_date
            and business_days_between(case.rfs_complete_date, case.as_of) > limit
        ):
            flags.append(
                FlagFinding(
                    code="RFS_LETTER",
                    severity=FlagSeverity.high,
                    finding=(
                        "RFS decision is documented but no decision letter is "
                        "documented within the clock."
                    ),
                    next_step=(
                        "Confirm decision letters were issued to the Veteran (and to "
                        "the provider if denied for incompleteness)."
                    ),
                )
            )

    # Flag 2 — Urgent/Complex coordination: cancelled, or no nurse follow-up
    # within threshold
    if urgent_or_complex:
        limit = rules["no_action_days_urgent_complex"]
        if case.consult_status == ConsultStatus.cancelled:
            flags.append(
                FlagFinding(
                    code="COORD_CANCELLED",
                    severity=FlagSeverity.high,
                    finding=(
                        f"{case.coordination_level.value} coordination case was "
                        "cancelled."
                    ),
                    next_step=(
                        "Confirm documented nurse follow-up and Veteran contact "
                        "before closure."
                    ),
                )
            )
        elif case.consult_status == ConsultStatus.active and (
            idle_days is None or idle_days > limit
        ):
            detail = (
                "no documented nurse action"
                if idle_days is None
                else f"{idle_days} days since the last nurse action"
            )
            flags.append(
                FlagFinding(
                    code="COORD_TIMELINESS",
                    severity=FlagSeverity.high,
                    finding=(
                        f"{case.coordination_level.value} coordination case with "
                        f"{detail} (threshold {limit} days)."
                    ),
                    next_step=(
                        "Assign nurse follow-up and document the care coordination "
                        "action."
                    ),
                )
            )

    # Flag 3 — death reported on a consult of any status (an active consult with a
    # reported death is the most urgent case), related to (or not ruled out from)
    # authorized care
    if case.death_reported and case.death_related_to_authorized_care is not False:
        relation = (
            "related to"
            if case.death_related_to_authorized_care
            else "relationship undetermined for"
        )
        flags.append(
            FlagFinding(
                code="DEATH_REPORTED",
                severity=FlagSeverity.critical,
                finding=(
                    f"Death reported; {relation} authorized care; consult "
                    f"{case.consult_status.value.lower()}."
                ),
                next_step="Route for patient safety review per the local process.",
            )
        )

    # Flag 4 — High Risk marker, Urgent, or Complex/Chronic; still active; no
    # action beyond threshold
    if (urgent_or_complex or case.high_risk) and (
        case.consult_status == ConsultStatus.active
    ):
        limit = rules["no_action_days_high_risk"]
        if idle_days is None or idle_days > limit:
            label = case.coordination_level.value + (
                " (High Risk)" if case.high_risk else ""
            )
            detail = (
                "no documented action"
                if idle_days is None
                else f"{idle_days} days with no action"
            )
            flags.append(
                FlagFinding(
                    code="NO_ACTION_LONG",
                    severity=FlagSeverity.critical,
                    finding=f"{label} case with {detail} (threshold {limit} days).",
                    next_step=(
                        "Immediate nurse review for patient safety and timeliness "
                        "of care."
                    ),
                )
            )

    # Flag 5 — Best Medical Interest (BMI) policy noncompliance
    if case.bmi_eligibility:
        flags.extend(_bmi_flags(case))

    return FlagCaseOutput(
        case_id=case.case_id,
        flagged=bool(flags),
        flags=flags,
        thresholds_used=rules,
        boundary=FLAG_BOUNDARY_NOTICE,
    )


def _bmi_flags(case: FlagCaseInput) -> list[FlagFinding]:
    """Flag 5 sub-rules for a Best Medical Interest case."""
    bmi = FLAG_CONFIG["bmi"]
    flags: list[FlagFinding] = []

    # 5a. Second review present after the Dole Act removed it (a missing date is
    # treated as possibly post-change)
    if case.bmi_second_review_documented and (
        case.bmi_determination_date is None
        or case.bmi_determination_date >= bmi["second_review_removed_on"]
    ):
        flags.append(
            FlagFinding(
                code="BMI_SECOND_REVIEW",
                severity=FlagSeverity.high,
                finding=(
                    "A second review is documented on a BMI determination. The "
                    "joint Veteran and referring clinician decision is final and no "
                    "longer requires a second review."
                ),
                next_step=(
                    "Review the local process for a residual second-review step and "
                    "consult delay."
                ),
            )
        )

    # 5b. Cancelled without a proper cancellation reason
    if case.consult_status == ConsultStatus.cancelled:
        reason = (case.bmi_cancel_reason or "").strip().lower()
        if not reason:
            flags.append(
                FlagFinding(
                    code="BMI_CANCEL_REASON",
                    severity=FlagSeverity.high,
                    finding=(
                        "BMI consult was cancelled with no cancellation reason "
                        "documented."
                    ),
                    next_step=(
                        "Obtain and document the cancellation reason per the BMI "
                        "guideline; confirm the Veteran was informed."
                    ),
                )
            )
        elif reason not in bmi["allowed_cancel_reasons"]:
            flags.append(
                FlagFinding(
                    code="BMI_CANCEL_REASON",
                    severity=FlagSeverity.high,
                    finding=(
                        "BMI consult was cancelled with a reason not on the accepted "
                        f"list: '{case.bmi_cancel_reason}'."
                    ),
                    next_step=(
                        "Verify the reason against the BMI guideline; a disagreement "
                        "with the Veteran goes to Clinical Appeals."
                    ),
                )
            )

    # 5c. No documented joint agreement
    if case.bmi_agreement_documented is not True:
        flags.append(
            FlagFinding(
                code="BMI_NO_AGREEMENT",
                severity=FlagSeverity.review,
                finding=(
                    "No documented joint agreement between the Veteran and the "
                    "referring clinician for the BMI determination."
                ),
                next_step=(
                    "Confirm the agreement is documented; BMI is final once both agree."
                ),
            )
        )

    # 5d. BMI used for a service that other law excludes
    if case.service_type and any(
        x in case.service_type.lower() for x in bmi["excluded_services"]
    ):
        flags.append(
            FlagFinding(
                code="BMI_EXCLUDED_SERVICE",
                severity=FlagSeverity.high,
                finding=(
                    f"BMI used for '{case.service_type}', a service where other "
                    "law-based criteria apply."
                ),
                next_step="Verify the correct eligibility pathway for this service.",
            )
        )

    return flags
