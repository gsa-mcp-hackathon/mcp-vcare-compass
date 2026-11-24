"""Tests for the Genie client behind ask_vcare_case_data (no network)."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from mcp_vcare_compass import genie
from mcp_vcare_compass.config import settings
from mcp_vcare_compass.models import AskCaseDataInput
from mcp_vcare_compass.notices import CASE_DATA_BOUNDARY_NOTICE

SPACE = "space-123"


def _message(conversation_id="conv-1", attachments=None, error=None):
    return NS(
        status=NS(value="COMPLETED"),
        conversation_id=conversation_id,
        message_id="msg-1",
        error=error,
        attachments=attachments
        if attachments is not None
        else [
            NS(
                attachment_id="att-q",
                text=None,
                suggested_questions=None,
                query=NS(query="SELECT COUNT(*) AS n FROM t"),
            ),
            NS(
                attachment_id="att-s",
                text=None,
                query=None,
                suggested_questions=NS(questions=["By facility?"]),
            ),
            NS(
                attachment_id="att-t",
                query=None,
                suggested_questions=None,
                text=NS(content="There are **200** high-risk cases."),
            ),
        ],
    )


class FakeGenie:
    def __init__(self, message=None, rows=None, raise_on=None, preview_error=None):
        self.message = message or _message()
        self.rows = rows if rows is not None else [["200"]]
        self.raise_on = raise_on
        self.preview_error = preview_error
        self.calls: list[tuple] = []

    def start_conversation_and_wait(self, space_id, content, timeout):
        self.calls.append(("start", space_id, content))
        if self.raise_on:
            raise self.raise_on
        return self.message

    def create_message_and_wait(self, space_id, conversation_id, content, timeout):
        self.calls.append(("follow_up", space_id, conversation_id, content))
        if self.raise_on:
            raise self.raise_on
        return self.message

    def get_message_attachment_query_result(self, *ids):
        self.calls.append(("result", *ids))
        if self.preview_error:
            raise self.preview_error
        manifest = NS(schema=NS(columns=[NS(name="n")]), total_row_count=len(self.rows))
        return NS(
            statement_response=NS(manifest=manifest, result=NS(data_array=self.rows))
        )


def client(fake: FakeGenie):
    return NS(genie=fake)


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(settings, "genie_space_id", SPACE)


def test_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "genie_space_id", "")
    fake = FakeGenie()
    out = genie.ask_genie(AskCaseDataInput(question="How many?"), client(fake))
    assert out.status == "ERROR"
    assert "GENIE_SPACE_ID" in out.error
    assert fake.calls == []


def test_empty_question_is_rejected_without_calling_genie():
    fake = FakeGenie()
    out = genie.ask_genie(AskCaseDataInput(question="   "), client(fake))
    assert (out.status, out.error) == ("ERROR", "question must not be empty.")
    assert fake.calls == []


def test_new_question_returns_answer_sql_and_rows():
    fake = FakeGenie()
    out = genie.ask_genie(AskCaseDataInput(question=" How many? "), client(fake))
    assert fake.calls[0] == ("start", SPACE, "How many?")
    assert fake.calls[1] == ("result", SPACE, "conv-1", "msg-1", "att-q")
    assert out.status == "COMPLETED"
    assert out.answer == "There are **200** high-risk cases."
    assert out.sql == "SELECT COUNT(*) AS n FROM t"
    assert (out.columns, out.rows, out.total_row_count) == (["n"], [["200"]], 1)
    assert out.rows_truncated is False
    assert out.suggested_questions == ["By facility?"]
    assert out.conversation_id == "conv-1"
    assert out.error is None
    assert out.boundary == CASE_DATA_BOUNDARY_NOTICE


def test_follow_up_continues_the_conversation():
    fake = FakeGenie()
    genie.ask_genie(
        AskCaseDataInput(question="By facility", conversation_id="conv-1"),
        client(fake),
    )
    assert fake.calls[0] == ("follow_up", SPACE, "conv-1", "By facility")


def test_result_preview_is_capped(monkeypatch):
    monkeypatch.setattr(settings, "genie_preview_rows", 20)
    fake = FakeGenie(rows=[[str(i)] for i in range(25)])
    out = genie.ask_genie(AskCaseDataInput(question="List"), client(fake))
    assert len(out.rows) == 20
    assert out.total_row_count == 25
    assert out.rows_truncated is True


def test_timeout_is_reported():
    fake = FakeGenie(raise_on=TimeoutError())
    out = genie.ask_genie(
        AskCaseDataInput(question="Slow", conversation_id="conv-9"), client(fake)
    )
    assert out.status == "TIMEOUT"
    assert out.conversation_id == "conv-9"


def test_service_error_is_reported_not_raised():
    fake = FakeGenie(raise_on=PermissionError("User lacks CAN RUN on space"))
    out = genie.ask_genie(AskCaseDataInput(question="How many?"), client(fake))
    assert out.status == "ERROR"
    assert out.error == "Genie request failed: User lacks CAN RUN on space"


def test_preview_failure_keeps_the_answer():
    fake = FakeGenie(preview_error=RuntimeError("statement expired"))
    out = genie.ask_genie(AskCaseDataInput(question="How many?"), client(fake))
    assert out.answer == "There are **200** high-risk cases."
    assert out.sql is not None
    assert "statement expired" in out.error


def test_genie_message_error_is_surfaced():
    message = _message(attachments=[], error=NS(error="Query failed"))
    out = genie.ask_genie(
        AskCaseDataInput(question="Bad"), client(FakeGenie(message=message))
    )
    assert out.error == "Query failed"
    assert out.answer is None
