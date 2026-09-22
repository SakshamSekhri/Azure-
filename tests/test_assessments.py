from backend.app.models.skill import Skill
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
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
