"""Boundary notices returned with every tool result.

These state what each tool is NOT: a compliance certification or a clinical
determination. Change the wording here only with the policy owner's sign-off.
"""

from __future__ import annotations

BOUNDARY_NOTICE = (
    "This checklist surfaces standardized GEMBA observation questions and policy "
    "citations to support a consult pathway review. It does NOT certify compliance, "
    "make a clinical determination, or substitute for the reviewing clinician's or "
    "auditor's judgment. The finding for any specific consult is recorded and judged "
    "by the human reviewer."
)

FLAG_BOUNDARY_NOTICE = (
    "Prototype screening flag only, run on synthetic data only. It is NOT a "
    "clinical determination and does not replace review by a qualified clinician. A "
    "flag means a case may warrant timely human review; no flag does not mean a case "
    "is safe."
)

CASE_DATA_BOUNDARY_NOTICE = (
    "Answers come from 100% synthetic VA Community Care consult data. Risk levels "
    "and compliance flags are administrative test priorities, NOT clinical "
    "determinations, and do not replace review by a qualified clinician or auditor."
)
