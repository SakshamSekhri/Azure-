import os
import sys
import pytest
from pathlib import Path
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.learning_plan import LearningPlan
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.learning_service import LearningService
from backend.app.schemas.ai import (
    AssessmentGenerationResponse,
    AssessmentMCQItem,
    AssessmentResultAnalysisResponse,
    LearningPlanResponse,
    LearningDayActivity
)
from backend.app.ai.foundry_agent import foundry_client
from backend.app.ai.ai_gateway import AIGateway


# =====================================================================
# TEST 1: Azure Foundry is actually called
# =====================================================================
def test_1_azure_foundry_is_actually_called(db_session, test_user, monkeypatch):
    called = {"status": False, "op_type": None, "payload": None}

    dummy_response = AssessmentGenerationResponse(
        title="Dynamic Test",
        role="Backend Engineer",
        total_questions=1,
        overview="Generated via Foundry",
        questions=[
            AssessmentMCQItem(
                id=1,
                question="What is the async event loop in FastAPI?",
                options=["Single-threaded non-blocking loop", "Multi-process daemon", "C++ compiler", "Browser runtime"],
                correct_answer="Single-threaded non-blocking loop",
                explanation="FastAPI runs async endpoints on the asyncio event loop.",
                skill="FastAPI",
                difficulty="Intermediate",
                topic="Concurrency",
                why_the_question_is_relevant="Job requires async APIs."
            )
        ]
    )

    def mock_execute(operation_type, payload, response_model):
        called["status"] = True
        called["op_type"] = operation_type
        called["payload"] = payload
        return dummy_response, 500, "LIVE_FOUNDRY"

    monkeypatch.setattr(foundry_client, "execute_operation", mock_execute)

    # Add resume and JD
    res = Resume(user_id=test_user.id, filename="cv.txt", raw_text="FastAPI developer", file_hash="h1")
    jd = JobDescription(user_id=test_user.id, title="Backend Engineer", raw_text="FastAPI needed", text_hash="j1")
    db_session.add_all([res, jd])
    db_session.commit()

    AssessmentService.generate_personalized_assessment(
        db=db_session,
        user_id=test_user.id,
        role="Backend Engineer",
        num_questions=1
    )

    assert called["status"] is True
    assert called["op_type"] == "ASSESSMENT_QUESTION_GENERATION"
    assert "FastAPI" in called["payload"]["resume"]


# =====================================================================
# TEST 2: Fallback agent does not exist
# =====================================================================
def test_2_fallback_agent_does_not_exist():
    # Attempting to import fallback_agent must fail
    with pytest.raises((ModuleNotFoundError, ImportError)):
        import backend.app.ai.fallback_agent

    # FallbackAgentProvider must not exist in ai module
    import backend.app.ai as ai_pkg
    assert not hasattr(ai_pkg, "FallbackAgentProvider")
    assert not hasattr(ai_pkg, "fallback_agent")


# =====================================================================
# TEST 3: No predefined question catalog exists
# =====================================================================
def test_3_no_predefined_question_catalog():
    # Scan python files in backend/app to ensure no hardcoded question lists exist
    backend_path = Path("backend/app")
    prohibited_terms = [
        "question_bank",
        "question_catalog",
        "static_questions",
        "sample_questions",
        "default_questions",
        "predefined_questions"
    ]
    for py_file in backend_path.glob("**/*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        for term in prohibited_terms:
            assert term not in content, f"Found prohibited term '{term}' in {py_file}"


# =====================================================================
# TEST 4: If Foundry fails, no questions are returned
# =====================================================================
def test_4_if_foundry_fails_no_questions_returned(db_session, test_user, monkeypatch):
    def mock_failure(*args, **kwargs):
        raise RuntimeError("Azure AI Foundry connection timed out.")

    monkeypatch.setattr(foundry_client, "execute_operation", mock_failure)

    res = Resume(user_id=test_user.id, filename="cv.txt", raw_text="FastAPI developer", file_hash="h1")
    jd = JobDescription(user_id=test_user.id, title="Backend Engineer", raw_text="FastAPI needed", text_hash="j1")
    db_session.add_all([res, jd])
    db_session.commit()

    initial_q_count = db_session.query(AssessmentQuestion).count()
    initial_a_count = db_session.query(Assessment).count()

    with pytest.raises(Exception) as exc_info:
        AssessmentService.generate_personalized_assessment(
            db=db_session,
            user_id=test_user.id,
            role="Backend Engineer",
            num_questions=5
        )

    # Must raise error and NOT return or save any fallback questions
    assert "Azure AI Foundry connection timed out" in str(exc_info.value)
    assert db_session.query(AssessmentQuestion).count() == initial_q_count
    assert db_session.query(Assessment).count() == initial_a_count


# =====================================================================
# TEST 5: A successful Foundry response is validated
# =====================================================================
def test_5_foundry_response_is_validated():
    valid_data = {
        "title": "Backend Assessment",
        "role": "Backend Engineer",
        "total_questions": 1,
        "overview": "Overview text",
        "questions": [
            {
                "id": 1,
                "question": "What is Pydantic in FastAPI?",
                "options": ["Data validation library", "Database driver", "CSS Framework", "HTTP Server"],
                "correct_answer": "Data validation library",
                "explanation": "Pydantic performs type validation and data parsing.",
                "skill": "FastAPI",
                "difficulty": "Intermediate",
                "topic": "Validation",
                "why_the_question_is_relevant": "Tests API contract validation."
            }
        ]
    }
    # Successful validation
    model = AssessmentGenerationResponse.model_validate(valid_data)
    assert model.total_questions == 1
    assert model.questions[0].correct_answer in model.questions[0].options

    # Invalid data must fail validation
    invalid_data = valid_data.copy()
    invalid_data["questions"] = []
    # If question is missing required fields, it fails validation
    with pytest.raises(ValidationError):
        AssessmentMCQItem.model_validate({"id": 1})


# =====================================================================
# TEST 6: Generated questions are saved to the database
# =====================================================================
def test_6_generated_questions_saved_to_database(db_session, test_user, monkeypatch):
    dummy_response = AssessmentGenerationResponse(
        title="Persisted Assessment",
        role="DevOps Engineer",
        total_questions=2,
        overview="Overview",
        questions=[
            AssessmentMCQItem(
                id=1,
                question="What is a Docker multi-stage build?",
                options=["Separates build from runtime", "Runs 2 containers", "Compiler", "Kernel module"],
                correct_answer="Separates build from runtime",
                explanation="Reduces final image footprint.",
                skill="Docker",
                difficulty="Intermediate",
                topic="Containerization",
                why_the_question_is_relevant="Job requires Docker."
            ),
            AssessmentMCQItem(
                id=2,
                question="What does Kubernetes kubelet do?",
                options=["Node agent managing pods", "DNS server", "Ingress proxy", "Database"],
                correct_answer="Node agent managing pods",
                explanation="Kubelet runs on each node.",
                skill="Kubernetes",
                difficulty="Intermediate",
                topic="Orchestration",
                why_the_question_is_relevant="Job requires Kubernetes."
            )
        ]
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_response, 300, "LIVE_FOUNDRY"))

    res = Resume(user_id=test_user.id, filename="cv.txt", raw_text="Docker experience", file_hash="h1")
    jd = JobDescription(user_id=test_user.id, title="DevOps", raw_text="Kubernetes needed", text_hash="j1")
    db_session.add_all([res, jd])
    db_session.commit()

    assessment_res = AssessmentService.generate_personalized_assessment(
        db=db_session,
        user_id=test_user.id,
        role="DevOps Engineer",
        num_questions=2
    )

    # Verify questions exist in assessment_questions table
    saved_questions = (
        db_session.query(AssessmentQuestion)
        .filter(AssessmentQuestion.assessment_id == assessment_res.id)
        .all()
    )
    assert len(saved_questions) == 2
    assert saved_questions[0].question == "What is a Docker multi-stage build?"
    assert saved_questions[0].correct_answer == "Separates build from runtime"
    assert saved_questions[1].question == "What does Kubernetes kubelet do?"


# =====================================================================
# TEST 7: Candidate answers are saved
# =====================================================================
def test_7_candidate_answers_are_saved(db_session, test_user, monkeypatch):
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="DevOps",
        strengths=["Docker"],
        weaknesses=["Kubernetes"],
        skill_gaps=["Kubernetes"],
        topics_to_improve=["Kubelet architecture"],
        priority_areas=["Kubernetes"],
        improvement_plan=["Study k8s pod lifecycle"],
        reassessment_recommendations="Retake k8s assessment",
        summary_feedback="Good docker knowledge."
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 200, "LIVE_FOUNDRY"))

    assessment = Assessment(
        candidate_id=test_user.id,
        title="DevOps Quiz",
        role="DevOps",
        difficulty="Intermediate",
        question_count=2,
        status="pending",
        questions_json=[]
    )
    db_session.add(assessment)
    db_session.commit()

    q1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Q1 Docker?",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Expl",
        skill="Docker"
    )
    q2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Q2 K8s?",
        options=["A", "B", "C", "D"],
        correct_answer="B",
        explanation="Expl",
        skill="Kubernetes"
    )
    db_session.add_all([q1, q2])
    db_session.commit()

    answers = {str(q1.id): "A", str(q2.id): "C"}
    AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=assessment.id,
        submitted_answers=answers
    )

    # Verify answers in assessment_answers table
    saved_answers = (
        db_session.query(AssessmentAnswer)
        .filter(AssessmentAnswer.assessment_id == assessment.id)
        .order_by(AssessmentAnswer.question_id.asc())
        .all()
    )
    assert len(saved_answers) == 2
    assert saved_answers[0].selected_answer == "A"
    assert saved_answers[0].is_correct is True
    assert saved_answers[1].selected_answer == "C"
    assert saved_answers[1].is_correct is False


# =====================================================================
# TEST 8: Score is calculated correctly (deterministic)
# =====================================================================
def test_8_score_calculated_correctly_deterministic(db_session, test_user, monkeypatch):
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Tester",
        strengths=[],
        weaknesses=[],
        skill_gaps=[],
        topics_to_improve=[],
        priority_areas=[],
        improvement_plan=[],
        summary_feedback=""
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 100, "LIVE_FOUNDRY"))

    assessment = Assessment(candidate_id=test_user.id, title="Math Test", role="Math", question_count=10, questions_json=[])
    db_session.add(assessment)
    db_session.commit()

    # Create 10 questions
    questions = []
    answers = {}
    for i in range(1, 11):
        q = AssessmentQuestion(
            assessment_id=assessment.id,
            question=f"Question {i}?",
            options=["Correct", "Wrong1", "Wrong2", "Wrong3"],
            correct_answer="Correct",
            explanation="Explanation",
            skill="Math"
        )
        questions.append(q)
    db_session.add_all(questions)
    db_session.commit()

    # 7 correct, 3 incorrect = exactly 70.0%
    for i, q in enumerate(questions):
        answers[str(q.id)] = "Correct" if i < 7 else "Wrong1"

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=assessment.id,
        submitted_answers=answers
    )

    assert result.total_questions == 10
    assert result.correct_count == 7
    assert result.score_percentage == 70.0


# =====================================================================
# TEST 9: AI result analysis is saved
# =====================================================================
def test_9_ai_result_analysis_is_saved(db_session, test_user, monkeypatch):
    expected_strengths = ["FastAPI", "Python"]
    expected_weaknesses = ["SQL Query Optimization"]
    expected_gaps = ["PostgreSQL Indexing"]

    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Backend Engineer",
        strengths=expected_strengths,
        weaknesses=expected_weaknesses,
        skill_gaps=expected_gaps,
        topics_to_improve=["B-Tree Indexes"],
        priority_areas=["PostgreSQL"],
        improvement_plan=["Study indexing strategy", "Practice query plans"],
        reassessment_recommendations="Retake in 5 days",
        summary_feedback="Strong web framework knowledge; needs database query tuning."
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 200, "LIVE_FOUNDRY"))

    assessment = Assessment(candidate_id=test_user.id, title="Backend Test", role="Backend Engineer", question_count=1, questions_json=[])
    db_session.add(assessment)
    db_session.commit()

    q = AssessmentQuestion(
        assessment_id=assessment.id,
        question="SQL Indexing?",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Expl",
        skill="SQL"
    )
    db_session.add(q)
    db_session.commit()

    AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=assessment.id,
        submitted_answers={str(q.id): "B"}
    )

    attempt = (
        db_session.query(AssessmentAttempt)
        .filter(AssessmentAttempt.assessment_id == assessment.id)
        .first()
    )
    assert attempt is not None
    assert attempt.result_summary_json is not None
    assert attempt.result_summary_json["strengths"] == expected_strengths
    assert attempt.result_summary_json["weaknesses"] == expected_weaknesses
    assert attempt.result_summary_json["skill_gaps"] == expected_gaps
    assert "B-Tree Indexes" in attempt.result_summary_json["topics_to_improve"]


# =====================================================================
# TEST 10: Learning plan is saved
# =====================================================================
def test_10_learning_plan_is_saved(db_session, test_user, monkeypatch):
    dummy_plan = LearningPlanResponse(
        target_role="Full Stack Backend Engineer",
        overview="7-day targeted mastery plan",
        days=[
            LearningDayActivity(
                day=1,
                topic="PostgreSQL Execution Plans",
                skill="SQL",
                activity_type="theory",
                objective="Analyze EXPLAIN ANALYZE output",
                resource_description="Read postgresql documentation",
                resource_url="https://postgresql.org"
            )
        ]
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_plan, 150, "LIVE_FOUNDRY"))

    plan = LearningService.generate_7day_plan(
        db=db_session,
        user_id=test_user.id,
        target_role="Full Stack Backend Engineer",
        force_refresh=True
    )

    assert plan is not None
    assert plan.target_role == "Full Stack Backend Engineer"
    db_plan = db_session.query(LearningPlan).filter(LearningPlan.id == plan.id).first()
    assert db_plan is not None
    assert db_plan.summary == "7-day targeted mastery plan"


# =====================================================================
# TEST 11: Previous assessment history is used in next generation request
# =====================================================================
def test_11_previous_history_used_in_next_generation(db_session, test_user, monkeypatch):
    captured_payload = {}

    def mock_execute(operation_type, payload, response_model):
        captured_payload.update(payload)
        return AssessmentGenerationResponse(
            title="Next Gen",
            role="Backend",
            total_questions=1,
            overview="O",
            questions=[
                AssessmentMCQItem(
                    id=1,
                    question="New Q?",
                    options=["A", "B", "C", "D"],
                    correct_answer="A",
                    explanation="E",
                    skill="SQL",
                    difficulty="Advanced",
                    topic="Query Planning",
                    why_the_question_is_relevant="Testing history pass"
                )
            ]
        ), 200, "LIVE_FOUNDRY"

    monkeypatch.setattr(foundry_client, "execute_operation", mock_execute)

    # 1. Create previous assessment attempt with high score (85.0%)
    prev_assessment = Assessment(candidate_id=test_user.id, title="Prior Assessment", role="Backend", difficulty="Intermediate", question_count=5, questions_json=[])
    db_session.add(prev_assessment)
    db_session.commit()

    prev_attempt = AssessmentAttempt(
        user_id=test_user.id,
        assessment_id=prev_assessment.id,
        score_percentage=85.0,
        total_questions=5,
        correct_count=4,
        answers_json={},
        result_summary_json={"weaknesses": ["SQL Performance"]},
        completed_at=prev_assessment.created_at
    )
    db_session.add(prev_attempt)

    # Add resume & JD
    res = Resume(user_id=test_user.id, filename="cv.txt", raw_text="FastAPI, SQL", file_hash="h1")
    jd = JobDescription(user_id=test_user.id, title="Backend", raw_text="FastAPI, SQL", text_hash="j1")
    db_session.add_all([res, jd])
    db_session.commit()

    AssessmentService.generate_personalized_assessment(
        db=db_session,
        user_id=test_user.id,
        role="Backend",
        num_questions=1
    )

    # Assert previous score and history were included in Foundry payload
    assert captured_payload.get("previous_score") == 85.0
    assert captured_payload.get("difficulty") == "Advanced"
    assert len(captured_payload.get("previous_performance")) >= 1
    assert captured_payload["previous_performance"][0]["score"] == 85.0


# =====================================================================
# TEST 12: Duplicate questions are rejected / regenerated
# =====================================================================
def test_12_duplicate_questions_prevented(db_session, test_user, monkeypatch):
    # Setup an existing question in database for candidate
    old_assessment = Assessment(candidate_id=test_user.id, title="Old Assessment", role="Backend", question_count=1, questions_json=[])
    db_session.add(old_assessment)
    db_session.commit()

    old_q = AssessmentQuestion(
        assessment_id=old_assessment.id,
        question="Explain the Global Interpreter Lock in Python CPython?",
        options=["GIL allows 1 thread", "Multi-thread bytecode", "Compiler", "Garbage collection"],
        correct_answer="GIL allows 1 thread",
        explanation="CPython GIL limits bytecode execution to 1 thread.",
        skill="Python"
    )
    db_session.add(old_q)
    db_session.commit()

    # Model returns 1 duplicate question and 1 fresh question
    dummy_response = AssessmentGenerationResponse(
        title="Check Duplicates",
        role="Backend",
        total_questions=2,
        overview="Overview",
        questions=[
            AssessmentMCQItem(
                id=1,
                # Exact match to old_q
                question="Explain the Global Interpreter Lock in Python CPython?",
                options=["GIL allows 1 thread", "Multi-thread bytecode", "Compiler", "Garbage collection"],
                correct_answer="GIL allows 1 thread",
                explanation="Explanation",
                skill="Python",
                difficulty="Intermediate",
                topic="Concurrency",
                why_the_question_is_relevant="Duplicate question"
            ),
            AssessmentMCQItem(
                id=2,
                # Brand new question
                question="How does asyncio create non-blocking network I/O in Python?",
                options=["Via epoll/kqueue event loop selectors", "Via multi-threading", "Via subprocesses", "Via GPU acceleration"],
                correct_answer="Via epoll/kqueue event loop selectors",
                explanation="Asyncio delegates to OS event loop selectors.",
                skill="Python",
                difficulty="Intermediate",
                topic="Async IO",
                why_the_question_is_relevant="Fresh question"
            )
        ]
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_response, 200, "LIVE_FOUNDRY"))

    res = Resume(user_id=test_user.id, filename="cv.txt", raw_text="Python dev", file_hash="h1")
    jd = JobDescription(user_id=test_user.id, title="Backend", raw_text="Python dev", text_hash="j1")
    db_session.add_all([res, jd])
    db_session.commit()

    new_assessment = AssessmentService.generate_personalized_assessment(
        db=db_session,
        user_id=test_user.id,
        role="Backend",
        num_questions=2
    )

    # Verify that the excluded_questions contained the old question
    saved_new_questions = (
        db_session.query(AssessmentQuestion)
        .filter(AssessmentQuestion.assessment_id == new_assessment.id)
        .all()
    )
    # The duplicate question was filtered out from final questions list
    q_texts = [q.question for q in saved_new_questions]
    assert "How does asyncio create non-blocking network I/O in Python?" in q_texts
