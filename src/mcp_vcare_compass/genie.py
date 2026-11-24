"""Genie agent client for ask_vcare_case_data.

Sends one natural-language question to the "Healthcare Risk and Coordination
Analysis" Genie agent and returns its answer, generated SQL, and a small result
preview. Failures are returned as a status + error message, never raised, so
the MCP client always gets an actionable reply.

Permissions (Databricks Apps): the app service principal needs CAN RUN on the
Genie space, CAN USE on its SQL warehouse, and SELECT on the tables the space
queries (the space runs as the caller).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from mcp_vcare_compass.config import settings
from mcp_vcare_compass.models import AskCaseDataInput, AskCaseDataOutput

_workspace_client: Any = None


def _client() -> Any:
    """Create the Databricks client lazily (credentials come from the env)."""
    global _workspace_client
    if _workspace_client is None:
        from databricks.sdk import WorkspaceClient

        _workspace_client = WorkspaceClient()
    return _workspace_client


def ask_genie(args: AskCaseDataInput, client: Any = None) -> AskCaseDataOutput:
    """Ask the Genie agent one question; optionally continue a conversation."""
    space_id = settings.genie_space_id
    if not space_id:
        return AskCaseDataOutput(
            status="ERROR", error="GENIE_SPACE_ID is not configured for this app."
        )
    question = (args.question or "").strip()
    if not question:
        return AskCaseDataOutput(status="ERROR", error="question must not be empty.")

    w = client or _client()
    timeout = timedelta(seconds=settings.genie_timeout_seconds)
    try:
        if args.conversation_id:
            msg = w.genie.create_message_and_wait(
                space_id, args.conversation_id, question, timeout=timeout
            )
        else:
            msg = w.genie.start_conversation_and_wait(
                space_id, question, timeout=timeout
            )
    except TimeoutError:
        return AskCaseDataOutput(
            status="TIMEOUT",
            conversation_id=args.conversation_id,
            error=(
                f"No answer within {settings.genie_timeout_seconds} seconds. "
                "Try a narrower question."
            ),
        )
    except Exception as e:  # permissions, bad conversation_id, service errors
        return AskCaseDataOutput(
            status="ERROR",
            conversation_id=args.conversation_id,
            error=f"Genie request failed: {e}",
        )

    out = AskCaseDataOutput(
        status=msg.status.value if msg.status else "UNKNOWN",
        conversation_id=msg.conversation_id,
    )
    if msg.error:
        out.error = getattr(msg.error, "error", None) or str(msg.error)

    texts: list[str] = []
    for att in msg.attachments or []:
        if att.text and att.text.content:
            texts.append(att.text.content)
        if att.suggested_questions and att.suggested_questions.questions:
            out.suggested_questions = list(att.suggested_questions.questions)
        if att.query and att.query.query and out.sql is None:
            out.sql = att.query.query
            _add_result_preview(w, space_id, msg, att.attachment_id, out)
    out.answer = "\n\n".join(texts) or None
    return out


def _add_result_preview(
    w: Any, space_id: str, msg: Any, attachment_id: str, out: AskCaseDataOutput
) -> None:
    """Attach up to `genie_preview_rows` result rows for a query attachment."""
    try:
        res = w.genie.get_message_attachment_query_result(
            space_id, msg.conversation_id, msg.message_id, attachment_id
        )
        sr = res.statement_response
        if sr and sr.manifest and sr.manifest.schema:
            out.columns = [c.name for c in (sr.manifest.schema.columns or [])]
        data = (sr.result.data_array if sr and sr.result else None) or []
        total = (
            sr.manifest.total_row_count
            if sr and sr.manifest and sr.manifest.total_row_count is not None
            else len(data)
        )
        out.total_row_count = total
        out.rows = data[: settings.genie_preview_rows]
        out.rows_truncated = total > len(out.rows)
    except Exception as e:
        out.error = (
            f"Answer generated, but the result preview could not be fetched: {e}"
        )
