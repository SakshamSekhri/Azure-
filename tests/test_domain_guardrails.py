import pytest
from backend.app.rag.guardrails import check_domain_guardrail
from backend.app.services.learning_service import LearningService


def test_elementary_science_guardrail_blocks_water():
    """Verify that elementary questions like 'whats water' are intercepted by Tier 3 guardrail."""
    oob, reason = check_domain_guardrail("whats water", active_role="Marketing Manager")
    assert oob is True
    assert "Elementary" in reason or "Everyday" in reason

    oob, reason = check_domain_guardrail("what is water", active_role="Software Engineer")
    assert oob is True

    oob, reason = check_domain_guardrail("tell me about water", active_role="Product Manager")
    assert oob is True

    oob, reason = check_domain_guardrail("why is water wet", active_role="Marketing Specialist")
    assert oob is True

    oob, reason = check_domain_guardrail("boiling point of water", active_role="Data Analyst")
    assert oob is True


def test_universal_off_topic_guardrail():
    """Verify that culinary, sports, gossip, and elementary nature questions are intercepted."""
    oob, _ = check_domain_guardrail("how to make a pizza", active_role="Marketing Manager")
    assert oob is True

    oob, _ = check_domain_guardrail("who won the world cup", active_role="Marketing Manager")
    assert oob is True

    oob, _ = check_domain_guardrail("why is the sky blue", active_role="Marketing Manager")
    assert oob is True

    oob, _ = check_domain_guardrail("tell me a joke", active_role="Marketing Manager")
    assert oob is True

    oob, _ = check_domain_guardrail("capital of france", active_role="Marketing Manager")
    assert oob is True


def test_role_valid_inquiries_allowed():
    """Verify that domain inquiries for active target roles are allowed through."""
    # Marketing domain inquiry for a marketing role
    oob, _ = check_domain_guardrail("explain CAC vs LTV in marketing", active_role="Marketing Manager")
    assert oob is False

    # Marketing strategy inquiry involving a consumer product (bottled water)
    oob, _ = check_domain_guardrail("how to market a bottled water brand", active_role="Marketing Manager")
    assert oob is False

    # Technical inquiry for a software role
    oob, _ = check_domain_guardrail("explain B-Tree vs Hash index", active_role="Software Engineer")
    assert oob is False

    # Waterfall SDLC inquiry for software role
    oob, _ = check_domain_guardrail("what is waterfall model in software engineering", active_role="Software Engineer")
    assert oob is False


def test_ask_grounded_question_rejects_water(db_session, test_user):
    """Verify LearningService.ask_grounded_question returns immediate Tier 3 response for 'whats water'."""
    res = LearningService.ask_grounded_question(
        db=db_session,
        user_id=test_user.id,
        question="whats water"
    )
    assert res.confidence == "None"
    assert res.grounded is False
    assert res.citations == []
    assert "strictly dedicated to career placement preparation" in res.answer
