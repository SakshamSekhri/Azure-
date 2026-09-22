from backend.app.ai.ai_gateway import AIGateway
from backend.app.schemas.ai import LearningPlanResponse, LearningDayActivity, AssessmentGenerationResponse, AssessmentMCQItem
from backend.app.models.ai_operation import AIOperation
from backend.app.ai.foundry_agent import foundry_client


def test_ai_gateway_caching_and_credit_control(db_session, test_user, monkeypatch):
    call_count = {"count": 0}

    dummy_plan = LearningPlanResponse(
        target_role="Backend Developer",
        overview="7-day backend roadmap",
        days=[
            LearningDayActivity(
                day=1,
                topic="FastAPI Async",
                skill="FastAPI",
                activity_type="theory",
                objective="Learn async event loop",
                resource_description="FastAPI docs",
                resource_url="https://fastapi.tiangolo.com"
            )
        ]
    )

    def mock_execute(operation_type, payload, response_model):
        call_count["count"] += 1
        return dummy_plan, 150, "LIVE_FOUNDRY"

    monkeypatch.setattr(foundry_client, "execute_operation", mock_execute)

    payload = {
        "target_role": "Backend Developer",
        "weak_skills": ["FastAPI", "SQL"],
        "strong_skills": ["Python"]
    }

    # First Call -> Executes Model / Provider
    res1 = AIGateway.execute(
        db=db_session,
        user_id=test_user.id,
        operation_type="LEARNING_PLAN",
        payload=payload,
        response_model=LearningPlanResponse,
        force_refresh=False
    )
    assert res1 is not None
    assert call_count["count"] == 1

    # Check that an operation was logged as LIVE_FOUNDRY
    op1 = db_session.query(AIOperation).filter(
        AIOperation.user_id == test_user.id,
        AIOperation.operation_type == "LEARNING_PLAN"
    ).order_by(AIOperation.created_at.desc()).first()

    assert op1 is not None
    assert op1.status == "LIVE_FOUNDRY"
    first_op_id = op1.operation_id

    # Second Call with EXACT SAME PAYLOAD -> Must hit cache with 0 new Foundry calls and 0 new tokens!
    res2 = AIGateway.execute(
        db=db_session,
        user_id=test_user.id,
        operation_type="LEARNING_PLAN",
        payload=payload,
        response_model=LearningPlanResponse,
        force_refresh=False
    )
    assert res2 is not None
    assert call_count["count"] == 1  # No new call made to Foundry!

    # Check the second audit record: status must be CACHED and tokens_used must be 0
    op2 = db_session.query(AIOperation).filter(
        AIOperation.user_id == test_user.id,
        AIOperation.operation_type == "LEARNING_PLAN"
    ).order_by(AIOperation.id.desc()).first()

    assert op2.status == "CACHED"
    assert op2.tokens_used == 0
    assert op2.request_metadata.get("cached_from_op_id") == first_op_id


def test_assessment_question_generation_never_cached(db_session, test_user, monkeypatch):
    """Proves requirement: assessment questions are never cached and are generated fresh."""
    q_call_count = {"count": 0}

    def mock_execute(operation_type, payload, response_model):
        q_call_count["count"] += 1
        return AssessmentGenerationResponse(
            title=f"Assessment Attempt {q_call_count['count']}",
            role="Backend Developer",
            total_questions=1,
            overview="Personalized assessment",
            questions=[
                AssessmentMCQItem(
                    id=q_call_count["count"],
                    question=f"Dynamic Question {q_call_count['count']}?",
                    options=["A", "B", "C", "D"],
                    correct_answer="A",
                    explanation="Explanation",
                    skill="FastAPI",
                    difficulty="Intermediate",
                    topic="Async",
                    why_the_question_is_relevant="Testing dynamic flow"
                )
            ]
        ), 200, "LIVE_FOUNDRY"

    monkeypatch.setattr(foundry_client, "execute_operation", mock_execute)

    payload = {
        "role": "Backend Developer",
        "resume": "Python, FastAPI",
        "job_description": "FastAPI Developer",
        "num_questions": 1
    }

    # Call 1
    res1 = AIGateway.execute(
        db=db_session,
        user_id=test_user.id,
        operation_type="ASSESSMENT_QUESTION_GENERATION",
        payload=payload,
        response_model=AssessmentGenerationResponse,
        force_refresh=False
    )
    # Call 2 with same payload
    res2 = AIGateway.execute(
        db=db_session,
        user_id=test_user.id,
        operation_type="ASSESSMENT_QUESTION_GENERATION",
        payload=payload,
        response_model=AssessmentGenerationResponse,
        force_refresh=False
    )

    # Must be called twice because questions must NEVER be cached
    assert q_call_count["count"] == 2
    assert res1.title != res2.title
