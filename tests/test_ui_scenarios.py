import pytest
from app import DEMO_TICKETS, get_pipeline


def test_demo_tickets_present():
    assert len(DEMO_TICKETS) == 6
    assert "1. Refund SLA (Safe Auto-Reply)" in DEMO_TICKETS
    assert "2. High Value + Escalation" in DEMO_TICKETS
    assert "3. Out of KB (Ownership Transfer)" in DEMO_TICKETS


def test_demo_ticket_1_auto_reply():
    pipeline = get_pipeline()
    res = pipeline.process_ticket(DEMO_TICKETS["1. Refund SLA (Safe Auto-Reply)"])
    from src.models import TriageAction
    assert res["decision"]["action"] in [TriageAction.AUTO_REPLY, TriageAction.CLARIFY]


def test_demo_ticket_2_escalates():
    pipeline = get_pipeline()
    res = pipeline.process_ticket(DEMO_TICKETS["2. High Value + Escalation"])
    assert res["decision"]["action"] == "ESCALATE"
    assert any("High monetary value" in r for r in res["decision"]["reasons"])


def test_demo_ticket_3_out_of_kb_escalates():
    pipeline = get_pipeline()
    res = pipeline.process_ticket(DEMO_TICKETS["3. Out of KB (Ownership Transfer)"])
    # Transferring to another student is forbidden / out of KB
    assert res["decision"]["action"] == "ESCALATE"
