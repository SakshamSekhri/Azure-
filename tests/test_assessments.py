from backend.app.models.skill import Skill
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.services.assessment_service import AssessmentService
from backend.app.schemas.ai import AssessmentResultAnalysisResponse, AssessmentGenerationResponse, AssessmentMCQItem
from backend.app.ai.foundry_agent import foundry_client
import pytest
from fastapi import HTTPException


def test_objective_mcq_assessment_scoring(db_session, test_user, monkeypatch):
    # Mock AI Result Analysis
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Python Engineer",
        strengths=["Python"],
        weaknesses=["Data Structures"],
        skill_gaps=["Data Structures"],
        topics_to_improve=["Tuples and Mutability"],
        priority_areas=["Python Internals"],
        improvement_plan=["Study memory layout of tuples"],
        reassessment_recommendations="Retake in 3 days",
        summary_feedback="Solid start."
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 100, "LIVE_FOUNDRY"))

    assessment = Assessment(
        candidate_id=test_user.id,
        title="Python Fundamentals Test",
        role="Python Engineer",
        difficulty="Beginner",
        question_count=2,
        status="pending",
        questions_json=[]
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    q1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is 2 + 2 in Python?",
        options=["3", "4", "5", "6"],
        correct_answer="4",
        explanation="2 + 2 = 4",
        skill="Python",
        topic="Math",
        difficulty="Beginner",
        why_the_question_is_relevant="Basic arithmetic test"
    )
    q2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Is tuple mutable in Python?",
        options=["Yes", "No", "Sometimes", "Never"],
        correct_answer="No",
        explanation="Tuples are immutable",
        skill="Python",
        topic="Data Structures",
        difficulty="Beginner",
        why_the_question_is_relevant="Testing data structure immutability"
    )
    db_session.add_all([q1, q2])
    db_session.commit()

    # 1. 100% Score Submission
    perfect_answers = {str(q1.id): "4", str(q2.id): "No"}
    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=assessment.id,
        submitted_answers=perfect_answers
    )

    assert result.score_percentage == 100.0
    assert result.correct_count == 2
    assert result.passed is True
    assert result.new_confidence == "High"
    assert result.new_demonstrated_level == "Advanced"

    # 2. 50% Score Submission
    half_answers = {str(q1.id): "4", str(q2.id): "Yes"}
    result_half = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=assessment.id,
        submitted_answers=half_answers
    )

    assert result_half.score_percentage == 50.0
    assert result_half.correct_count == 1
    assert result_half.passed is False
    assert result_half.new_confidence == "Medium"

    # 3. 0% Score Submission (Below 50% -> Low confidence)
    zero_answers = {str(q1.id): "3", str(q2.id): "Yes"}
    result_zero = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=assessment.id,
        submitted_answers=zero_answers
    )
    assert result_zero.score_percentage == 0.0
    assert result_zero.new_confidence == "Low"


def test_missing_resume_or_jd_validation_error(db_session, test_user):
    """Proves requirement 10: Missing resume or JD raises HTTP 400 validation error."""
    with pytest.raises(HTTPException) as exc_info:
        AssessmentService.generate_personalized_assessment(
            db=db_session,
            user_id=test_user.id,
            role="Backend Developer",
            resume_text="",
            jd_text=""
        )
    assert exc_info.value.status_code == 400
    assert "upload your resume" in exc_info.value.detail.lower()


def test_personalized_assessment_generation_and_storage(db_session, test_user, monkeypatch):
    # Upload dummy resume and JD
    resume = Resume(
        user_id=test_user.id,
        filename="cv.txt",
        raw_text="Experienced in Python, FastAPI, Docker, and PostgreSQL.",
        file_hash="hash123",
        parsed_data={"skills": [{"name": "Python"}, {"name": "FastAPI"}], "projects": [{"name": "E-Commerce API"}]}
    )
    jd = JobDescription(
        user_id=test_user.id,
        title="Backend Engineer",
        raw_text="Requirements: Python, FastAPI, Docker, Microservices, Redis.",
        text_hash="jdhash123",
        parsed_data={"required_skills": [{"name": "Python"}, {"name": "Docker"}, {"name": "Redis"}]}
    )
    db_session.add_all([resume, jd])
    db_session.commit()

    dummy_gen = AssessmentGenerationResponse(
        title="Personalized Backend Engineer Assessment",
        role="Backend Engineer",
        total_questions=3,
        overview="Assessment generated dynamically by Azure AI Foundry",
        questions=[
            AssessmentMCQItem(
                id=1,
                question="How does Redis operate in a Cache-Aside pattern for FastAPI?",
                options=["Reads cache first, on miss reads DB", "Writes only to cache", "Replaces DB entirely", "Runs inside browser"],
                correct_answer="Reads cache first, on miss reads DB",
                explanation="Cache-aside queries cache first and loads DB on miss.",
                skill="Redis",
                difficulty="Intermediate",
                topic="Caching",
                why_the_question_is_relevant="Candidate has FastAPI, JD requires Redis which is a skill gap."
            ),
            AssessmentMCQItem(
                id=2,
                question="In Docker multi-stage builds, what is the primary benefit?",
                options=["Reduces image size by separating build tools from runtime", "Runs multiple containers in one", "Compiles to x86 assembly", "Eliminates ports"],
                correct_answer="Reduces image size by separating build tools from runtime",
                explanation="Multi-stage builds produce minimal production containers.",
                skill="Docker",
                difficulty="Intermediate",
                topic="Containerization",
                why_the_question_is_relevant="Job requires Docker containerization."
            ),
            AssessmentMCQItem(
                id=3,
                question="In your project 'E-Commerce API', how do you handle concurrency?",
                options=["Asyncio event loop with non-blocking awaits", "Global interpreter lock locking all cores", "Single threaded blocking sleep", "Shared memory without mutex"],
                correct_answer="Asyncio event loop with non-blocking awaits",
                explanation="FastAPI event loop efficiently manages async requests.",
                skill="FastAPI",
                difficulty="Intermediate",
                topic="Concurrency",
                why_the_question_is_relevant="Candidate claimed 'E-Commerce API' built with FastAPI."
            )
        ]
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_gen, 450, "LIVE_FOUNDRY"))

    res = AssessmentService.generate_personalized_assessment(
        db=db_session,
        user_id=test_user.id,
        role="Backend Engineer",
        num_questions=3
    )

    assert res is not None
    assert res.id is not None
    assert res.total_questions == 3
    assert len(res.questions) == 3
    # Check that questions are saved in assessment_questions table
    db_q = db_session.query(AssessmentQuestion).filter(AssessmentQuestion.assessment_id == res.id).all()
    assert len(db_q) == 3
    assert db_q[0].correct_answer == "Reads cache first, on miss reads DB"
    assert db_q[0].why_the_question_is_relevant is not None


# =====================================================================
# REFACTORED ASSESSMENT SUITE: 14 REQUIRED ARCHITECTURAL TESTS
# =====================================================================

def _create_sample_assessment(db_session, user_id, title="Architecture Assessment", role="Python Architect"):
    """Helper to create a deterministic assessment with 2 questions."""
    asm = Assessment(
        candidate_id=user_id,
        title=title,
        role=role,
        difficulty="Intermediate",
        question_count=2,
        status="pending",
        questions_json=[]
    )
    db_session.add(asm)
    db_session.commit()
    db_session.refresh(asm)

    q1 = AssessmentQuestion(
        assessment_id=asm.id,
        question="What is the time complexity of dictionary lookup in Python?",
        options=["O(1)", "O(n)", "O(log n)", "O(n^2)"],
        correct_answer="O(1)",
        explanation="Python dictionaries use hash tables with average O(1) lookup.",
        skill="Python",
        topic="Data Structures",
        concept="Hash Tables",
        difficulty="Intermediate",
        why_the_question_is_relevant="Core knowledge of Python performance characteristics."
    )
    q2 = AssessmentQuestion(
        assessment_id=asm.id,
        question="What is GIL in CPython?",
        options=["Global Interpreter Lock", "General Integration Layer", "Global Index Locator", "Graph Inspection Log"],
        correct_answer="Global Interpreter Lock",
        explanation="GIL is a mutex that prevents multiple native threads from executing Python bytecodes simultaneously.",
        skill="Python",
        topic="Concurrency",
        concept="CPython Internals",
        difficulty="Intermediate",
        why_the_question_is_relevant="Essential for concurrent system design in Python."
    )
    db_session.add_all([q1, q2])
    db_session.commit()
    return asm, q1, q2


def test_1_submission_returns_fast_without_ai_blocking(db_session, test_user, monkeypatch):
    """1. Assessment submission returns quickly without waiting for AI analysis."""
    # Ensure AI is never called during submission
    ai_called = False
    def explode_if_called(*args, **kwargs):
        nonlocal ai_called
        ai_called = True
        raise RuntimeError("AI Foundry should not be called synchronously during submission!")

    monkeypatch.setattr(foundry_client, "execute_operation", explode_if_called)

    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    answers = {str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers
    )

    assert ai_called is False, "AIGateway must NOT be called synchronously during submission!"
    assert result is not None
    assert result.score_percentage == 100.0
    assert result.analysis_status == "pending"


def test_2_deterministic_score_is_persisted(db_session, test_user):
    """2. Deterministic score is persisted correctly in the database."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    # 1 correct, 1 wrong = 50%
    answers = {str(q1.id): "O(1)", str(q2.id): "Global Index Locator"}

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers
    )

    assert result.score_percentage == 50.0
    assert result.correct_count == 1
    assert result.passed is False

    # Check persistence in AssessmentAttempt table
    attempt = db_session.query(AssessmentAttempt).filter(AssessmentAttempt.id == result.attempt_id).first()
    assert attempt is not None
    assert attempt.score_percentage == 50.0
    assert attempt.correct_count == 1
    assert attempt.total_questions == 2


def test_3_assessment_attempt_is_created(db_session, test_user):
    """3. AssessmentAttempt record is created with attempt_number and deterministic summary."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    answers = {str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers
    )

    attempt = db_session.query(AssessmentAttempt).filter(AssessmentAttempt.id == result.attempt_id).first()
    assert attempt is not None
    assert attempt.attempt_number == 1
    assert attempt.user_id == test_user.id
    assert attempt.assessment_id == asm.id
    assert attempt.answers_json == answers
    assert attempt.analysis_status == "pending"
    assert "details" in attempt.result_summary_json
    assert len(attempt.result_summary_json["details"]) == 2


def test_4_assessment_answers_are_created(db_session, test_user):
    """4. AssessmentAnswer records are created for each question with attempt_id."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    answers = {str(q1.id): "O(1)", str(q2.id): "Wrong Answer"}

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers
    )

    ans_records = (
        db_session.query(AssessmentAnswer)
        .filter(AssessmentAnswer.attempt_id == result.attempt_id)
        .order_by(AssessmentAnswer.question_id.asc())
        .all()
    )
    assert len(ans_records) == 2
    assert ans_records[0].question_id == q1.id
    assert ans_records[0].selected_answer == "O(1)"
    assert ans_records[0].is_correct is True

    assert ans_records[1].question_id == q2.id
    assert ans_records[1].selected_answer == "Wrong Answer"
    assert ans_records[1].is_correct is False


def test_5_ai_analysis_runs_after_submission(db_session, test_user, monkeypatch):
    """5. AI diagnostic analysis runs asynchronously after submission without blocking."""
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Python Architect",
        strengths=["Python Hash Maps"],
        weaknesses=["CPython Concurrency"],
        skill_gaps=["CPython Concurrency"],
        topics_to_improve=["GIL Internals"],
        priority_areas=["Threading"],
        improvement_plan=["Study CPython source code for ceval.c"],
        reassessment_recommendations="Retake concurrency evaluation",
        summary_feedback="Excellent foundation on hash tables."
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 120, "LIVE_FOUNDRY"))

    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    answers = {str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers
    )
    assert result.analysis_status == "pending"

    # Now execute the background worker task
    AssessmentService._execute_ai_analysis_for_attempt(db_session, result.attempt_id, test_user.id, asm.id)

    # Verify attempt was updated
    updated_attempt = db_session.query(AssessmentAttempt).filter(AssessmentAttempt.id == result.attempt_id).first()
    assert updated_attempt.analysis_status == "completed"
    assert updated_attempt.result_summary_json["summary_feedback"] == "Excellent foundation on hash tables."
    assert "Study CPython source code for ceval.c" in updated_attempt.result_summary_json["improvement_plan"]
    # Deterministic scores remain intact
    assert updated_attempt.score_percentage == 100.0


def test_6_ai_failure_does_not_destroy_attempt(db_session, test_user, monkeypatch):
    """6. AI failure does not destroy the attempt or deterministic score."""
    def fail_operation(*args, **kwargs):
        raise RuntimeError("Azure AI Foundry gateway timeout 504")

    monkeypatch.setattr(foundry_client, "execute_operation", fail_operation)

    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    answers = {str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers
    )

    # Run AI analysis which will fail
    AssessmentService._execute_ai_analysis_for_attempt(db_session, result.attempt_id, test_user.id, asm.id)

    attempt = db_session.query(AssessmentAttempt).filter(AssessmentAttempt.id == result.attempt_id).first()
    assert attempt is not None, "Attempt must NOT be deleted if AI fails!"
    assert attempt.analysis_status == "failed"
    assert attempt.score_percentage == 100.0
    assert attempt.correct_count == 2
    assert "details" in attempt.result_summary_json
    assert len(attempt.result_summary_json["details"]) == 2


def test_7_history_returns_previous_attempts(db_session, test_user):
    """7. History endpoint returns previous attempt records with required metadata."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    answers1 = {str(q1.id): "O(1)", str(q2.id): "Wrong"}
    answers2 = {str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}

    # Attempt 1
    AssessmentService.submit_assessment(db_session, test_user.id, asm.id, answers1)
    # Attempt 2
    AssessmentService.submit_assessment(db_session, test_user.id, asm.id, answers2)

    history = AssessmentService.get_assessment_history(db_session, test_user.id)
    assert len(history) >= 2

    # Check that items contain all required attempt identification fields (Requirement 7)
    item = history[0]
    assert item.assessment_id == asm.id
    assert item.attempt_id is not None
    assert item.attempt_number is not None
    assert item.title is not None
    assert item.role is not None
    assert item.completed_at is not None
    assert item.score_percentage is not None
    assert item.total_questions == 2
    assert item.analysis_status in ("pending", "completed", "failed")


def test_8_multiple_attempts_are_preserved(db_session, test_user):
    """8. Multiple attempts for the same assessment are independently preserved."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)

    # Attempt 1: 50%
    res1 = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Wrong"}
    )
    # Attempt 2: 100%
    res2 = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}
    )

    assert res1.attempt_id != res2.attempt_id
    assert res1.attempt_number == 1
    assert res2.attempt_number == 2
    assert res1.score_percentage == 50.0
    assert res2.score_percentage == 100.0

    attempts = (
        db_session.query(AssessmentAttempt)
        .filter(AssessmentAttempt.assessment_id == asm.id, AssessmentAttempt.user_id == test_user.id)
        .order_by(AssessmentAttempt.attempt_number.asc())
        .all()
    )
    assert len(attempts) == 2
    assert attempts[0].score_percentage == 50.0
    assert attempts[1].score_percentage == 100.0


def test_9_older_attempt_can_be_opened_independently(db_session, test_user):
    """9. Older attempt can be opened independently via attempt-specific endpoint."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)

    res1 = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Wrong"}
    )
    res2 = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}
    )

    # Fetch attempt 1 explicitly
    att1_data = AssessmentService.get_assessment_attempt_result(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        attempt_id=res1.attempt_id
    )
    assert att1_data.attempt_id == res1.attempt_id
    assert att1_data.attempt_number == 1
    assert att1_data.score_percentage == 50.0
    assert att1_data.correct_count == 1

    # Fetch attempt 2 explicitly
    att2_data = AssessmentService.get_assessment_attempt_result(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        attempt_id=res2.attempt_id
    )
    assert att2_data.attempt_id == res2.attempt_id
    assert att2_data.attempt_number == 2
    assert att2_data.score_percentage == 100.0
    assert att2_data.correct_count == 2


def test_10_user_cannot_access_another_users_attempt(db_session, test_user):
    """10. User cannot access another user's assessment attempt."""
    from backend.app.models.user import User

    # Create second user
    other_user = User(
        email="hacker@example.com",
        password_hash="hash",
        is_active=True
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    res = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}
    )

    # other_user tries to access test_user's attempt
    with pytest.raises(HTTPException) as exc_info:
        AssessmentService.get_assessment_attempt_result(
            db=db_session,
            user_id=other_user.id,
            assessment_id=asm.id,
            attempt_id=res.attempt_id
        )
    assert exc_info.value.status_code in (403, 404)


def test_11_historical_review_does_not_regenerate_questions(db_session, test_user, monkeypatch):
    """11. Historical review does not regenerate questions or call AI."""
    ai_called = False
    def bomb(*args, **kwargs):
        nonlocal ai_called
        ai_called = True
        raise RuntimeError("Should never regenerate questions for history review!")

    monkeypatch.setattr(foundry_client, "execute_operation", bomb)

    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    res = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}
    )

    # Historical review
    review = AssessmentService.get_assessment_attempt_result(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        attempt_id=res.attempt_id
    )

    assert ai_called is False
    assert len(review.details) == 2
    assert review.details[0].question == q1.question
    assert review.details[0].selected_answer == "O(1)"
    assert review.details[0].correct_answer == "O(1)"
    assert review.details[0].is_correct is True


def test_12_review_works_when_ai_pending(db_session, test_user):
    """12. Review works completely when AI analysis is pending."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    res = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Wrong"}
    )
    assert res.analysis_status == "pending"

    review = AssessmentService.get_assessment_attempt_result(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        attempt_id=res.attempt_id
    )
    assert review.analysis_status == "pending"
    assert review.score_percentage == 50.0
    assert len(review.details) == 2
    assert review.details[0].explanation == q1.explanation


def test_13_review_works_when_ai_failed(db_session, test_user):
    """13. Review works completely when AI analysis failed."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    res = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers={str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}
    )

    # Manually mark as failed
    attempt = db_session.query(AssessmentAttempt).filter(AssessmentAttempt.id == res.attempt_id).first()
    attempt.analysis_status = "failed"
    attempt.result_summary_json["analysis_status"] = "failed"
    attempt.result_summary_json["analysis_error"] = "Service unavailable"
    db_session.commit()

    review = AssessmentService.get_assessment_attempt_result(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        attempt_id=res.attempt_id
    )
    assert review.analysis_status == "failed"
    assert review.score_percentage == 100.0
    assert len(review.details) == 2
    assert review.details[1].question == q2.question
    assert review.details[1].correct_answer == "Global Interpreter Lock"


def test_14_double_submission_safely_handled(db_session, test_user):
    """14. Accidental double submission is safely handled and does not create duplicate attempts."""
    asm, q1, q2 = _create_sample_assessment(db_session, test_user.id)
    answers = {str(q1.id): "O(1)", str(q2.id): "Global Interpreter Lock"}

    # First submission
    res1 = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers,
        idempotency_key="idemp-key-12345"
    )

    # Immediate second submission (e.g. user double-clicked)
    res2 = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=asm.id,
        submitted_answers=answers,
        idempotency_key="idemp-key-12345"
    )

    assert res1.attempt_id == res2.attempt_id, "Double submission must return the existing attempt!"

    # Total attempts count in database must be exactly 1
    total_attempts = (
        db_session.query(AssessmentAttempt)
        .filter(AssessmentAttempt.assessment_id == asm.id, AssessmentAttempt.user_id == test_user.id)
        .count()
    )
    assert total_attempts == 1
