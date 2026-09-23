import pytest
from fastapi import HTTPException
from backend.app.schemas.ai import AssessmentMCQItem, AssessmentGenerationResponse
from backend.app.services.assessment_service import (
    _validate_question_quality,
    _compute_question_hash,
    AssessmentService
)
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.ai.foundry_agent import foundry_client


def test_question_quality_validation_valid():
    q = AssessmentMCQItem(
        id=1,
        question="Which Python data structure provides O(1) average time complexity for key lookups?",
        options=["List", "Dictionary", "Tuple", "Linked List"],
        correct_answer="Dictionary",
        explanation="Dictionaries in Python are implemented as hash tables offering O(1) average lookups.",
        skill="Python",
        topic="Data Structures",
        difficulty="Intermediate",
        why_the_question_is_relevant="Essential for writing time-efficient backend code."
    )
    is_valid, reason = _validate_question_quality(q)
    assert is_valid is True
    assert reason == "Valid"


def test_question_quality_validation_too_short():
    q = AssessmentMCQItem(
        id=2,
        question="What is SQL?",
        options=["Query language", "Database", "Table", "Column"],
        correct_answer="Query language",
        explanation="SQL is Structured Query Language",
        skill="SQL",
        topic="Database"
    )
    is_valid, reason = _validate_question_quality(q)
    assert is_valid is False
    assert "too short" in reason


def test_question_quality_validation_fewer_than_four_options():
    q = AssessmentMCQItem(
        id=3,
        question="Which HTTP method is idempotent and used for updating entire resources?",
        options=["GET", "PUT", "POST"],
        correct_answer="PUT",
        explanation="PUT replaces target resource.",
        skill="REST APIs",
        topic="Web"
    )
    is_valid, reason = _validate_question_quality(q)
    assert is_valid is False
    assert "exactly 4 options" in reason


def test_question_quality_validation_duplicate_options():
    q = AssessmentMCQItem(
        id=4,
        question="Which indexing data structure is standard for B-tree based relational indexes?",
        options=["B-Tree", "B+Tree", "B-Tree", "Hash Map"],
        correct_answer="B+Tree",
        explanation="B+Tree allows efficient range scans.",
        skill="PostgreSQL",
        topic="Database Internals"
    )
    is_valid, reason = _validate_question_quality(q)
    assert is_valid is False
    assert "unique and distinct" in reason


def test_question_quality_validation_correct_answer_not_in_options():
    q = AssessmentMCQItem(
        id=5,
        question="In Docker, which directive sets the default executable for the container?",
        options=["RUN", "CMD", "EXPOSE", "ENV"],
        correct_answer="ENTRYPOINT",
        explanation="ENTRYPOINT sets the default command.",
        skill="Docker",
        topic="DevOps"
    )
    is_valid, reason = _validate_question_quality(q)
    assert is_valid is False
    assert "must match exactly one of the 4 options" in reason


def test_question_quality_validation_placeholder_options():
    q = AssessmentMCQItem(
        id=6,
        question="What is the primary function of an asynchronous event loop in Node.js?",
        options=["Option A", "Option B", "Option C", "Option D"],
        correct_answer="Option A",
        explanation="Placeholders are unacceptable.",
        skill="Node.js",
        topic="Concurrency"
    )
    is_valid, reason = _validate_question_quality(q)
    assert is_valid is False
    assert "placeholder" in reason


def test_question_quality_validation_answer_leakage():
    q = AssessmentMCQItem(
        id=7,
        question="In React, the answer is useEffect which handles component side effects in functional components?",
        options=["useState", "useEffect", "useMemo", "useCallback"],
        correct_answer="useEffect",
        explanation="Answer leaked in stem.",
        skill="React",
        topic="Hooks"
    )
    is_valid, reason = _validate_question_quality(q)
    assert is_valid is False
    assert "Answer leakage detected" in reason


def test_compute_question_hash_normalization():
    q1 = "What is Python GIL (Global Interpreter Lock)?"
    q2 = "What is python gil global interpreter lock"
    q3 = "What is Docker ENTRYPOINT vs CMD?"

    h1 = _compute_question_hash(q1)
    h2 = _compute_question_hash(q2)
    h3 = _compute_question_hash(q3)

    assert h1 == h2  # Case, punctuation, and spacing differences normalized to identical hash
    assert h1 != h3  # Distinct question has distinct hash


def test_zero_fallback_on_foundry_failure(db_session, test_user, monkeypatch):
    """Zero predefined question guarantee: when Foundry fails, HTTP 502 is raised, zero fallbacks."""
    def mock_failure(*args, **kwargs):
        raise RuntimeError("Azure AI Foundry network timeout")

    monkeypatch.setattr(foundry_client, "execute_operation", mock_failure)

    initial_assessment_count = db_session.query(Assessment).count()
    initial_question_count = db_session.query(AssessmentQuestion).count()

    with pytest.raises(HTTPException) as exc_info:
        AssessmentService.generate_personalized_assessment(
            db=db_session,
            user_id=test_user.id,
            role="Backend Engineer",
            resume_text="Python and backend engineer with 2 years experience",
            jd_text="Looking for Backend Engineer with Python and SQL",
            num_questions=3
        )

    # Must raise 502 Bad Gateway
    assert exc_info.value.status_code == 502
    assert "Unable to generate personalized assessment" in exc_info.value.detail

    # Zero questions or dummy assessments must be persisted
    assert db_session.query(Assessment).count() == initial_assessment_count
    assert db_session.query(AssessmentQuestion).count() == initial_question_count


def test_dynamic_generation_with_canonical_skill_and_hash(db_session, test_user, monkeypatch):
    """Dynamic generation successfully stores canonical_skill_id and question_hash."""
    valid_mcq1 = AssessmentMCQItem(
        id=1,
        question="Which PostgreSQL isolation level prevents non-repeatable reads and dirty reads?",
        options=["Read Uncommitted", "Read Committed", "Repeatable Read", "None"],
        correct_answer="Repeatable Read",
        explanation="Repeatable read ensures transactions see a snapshot.",
        skill="PostgreSQL",
        topic="Transactions",
        difficulty="Intermediate",
        why_the_question_is_relevant="Essential for data integrity in backend engineering."
    )
    valid_mcq2 = AssessmentMCQItem(
        id=2,
        question="What is the primary function of Write-Ahead Logging (WAL) in PostgreSQL database?",
        options=["Ensure durability and atomicity", "Compress query results", "Encrypt network packets", "Generate query execution plans"],
        correct_answer="Ensure durability and atomicity",
        explanation="WAL ensures changes are recorded before being committed.",
        skill="PostgreSQL",
        topic="Storage Engine",
        difficulty="Intermediate",
        why_the_question_is_relevant="Core requirement for high-availability systems."
    )
    gen_response = AssessmentGenerationResponse(
        title="Personalized Assessment",
        role="Backend Engineer",
        total_questions=2,
        difficulty="Intermediate",
        questions=[valid_mcq1, valid_mcq2]
    )
    # Monkeypatch foundry
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (gen_response, 120, "LIVE_FOUNDRY"))

    assessment_resp = AssessmentService.generate_personalized_assessment(
        db=db_session,
        user_id=test_user.id,
        role="Backend Engineer",
        resume_text="PostgreSQL and database backend developer",
        jd_text="Backend engineer proficient with PostgreSQL database systems",
        num_questions=2
    )

    assert assessment_resp.id is not None
    assert assessment_resp.role == "Backend Engineer"

    # Query persisted questions directly
    saved_questions = db_session.query(AssessmentQuestion).filter(
        AssessmentQuestion.assessment_id == assessment_resp.id
    ).all()

    assert len(saved_questions) >= 1
    for q in saved_questions:
        assert q.canonical_skill_id == "postgresql"
        assert q.question_hash is not None
        assert len(q.question_hash) == 64  # SHA256 hex length
