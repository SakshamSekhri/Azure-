import pytest
from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.skill_service import SkillService
from backend.app.schemas.ai import (
    AssessmentResultAnalysisResponse,
    AssessmentGenerationResponse,
    AssessmentMCQItem
)
from backend.app.ai.foundry_agent import foundry_client


def test_per_skill_score_calculation_and_persistence(db_session, test_user, monkeypatch):
    """Verify that:
    1. Assessment submissions calculate deterministic per-skill scores (e.g. Python 2/2=100%, SQL 1/2=50%, Docker 0/1=0%).
    2. StudentSkill records are directly updated in the database with assessment_score, demonstrated_level, confidence.
    3. Untested skills strictly retain assessment_score = NULL and Unassessed status.
    4. Skill Matrix reflects these scores immediately.
    """
    # 1. Setup Skills and StudentSkill records
    skills_data = [
        ("Python", "Programming"),
        ("SQL", "Database"),
        ("Docker", "DevOps"),
        ("React", "Frontend")  # Will remain untested
    ]
    skill_objs = {}
    for name, cat in skills_data:
        sk = db_session.query(Skill).filter(Skill.name == name).first()
        if not sk:
            sk = Skill(name=name, category=cat)
            db_session.add(sk)
            db_session.flush()
        skill_objs[name] = sk

        # Add claimed StudentSkill
        ss = StudentSkill(
            user_id=test_user.id,
            skill_id=sk.id,
            is_claimed=1,
            claimed_level="Intermediate",
            confidence="Low",
            assessment_score=None
        )
        db_session.add(ss)
    db_session.commit()

    # 2. Mock AI Result Analysis
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Backend Engineer",
        strengths=["Python"],
        weaknesses=["Docker"],
        skill_gaps=["Docker"],
        topics_to_improve=["Containerization"],
        priority_areas=["Docker Containers"],
        improvement_plan=["Practice Dockerfile syntax"],
        reassessment_recommendations="Reassess Docker in 3 days",
        summary_feedback="Strong Python understanding, requires practice in Docker."
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 100, "LIVE_FOUNDRY"))

    # 3. Create Assessment with questions spanning Python (2), SQL (2), and Docker (1)
    assessment = Assessment(
        candidate_id=test_user.id,
        title="Full Stack Competency Assessment",
        role="Backend Engineer",
        difficulty="Intermediate",
        question_count=5,
        status="pending",
        questions_json=[]
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    # 2 Python Questions
    q1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is a Python generator?",
        options=["A function yielding values", "A class", "A decorator", "A list"],
        correct_answer="A function yielding values",
        explanation="Generators use yield to produce a sequence lazily.",
        skill="Python",
        topic="Iterators",
        concept="Yield Mechanism",
        difficulty="Intermediate"
    )
    q2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is GIL in CPython?",
        options=["Global Interpreter Lock", "General Interface Link", "Global Index List", "None"],
        correct_answer="Global Interpreter Lock",
        explanation="GIL prevents multiple native threads from executing Python bytecodes at once.",
        skill="Python",
        topic="Concurrency",
        concept="GIL Lock Contention",
        difficulty="Intermediate"
    )
    # 2 SQL Questions
    q3 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Which SQL clause filters grouped rows?",
        options=["HAVING", "WHERE", "GROUP BY", "ORDER BY"],
        correct_answer="HAVING",
        explanation="HAVING filters groups created by GROUP BY.",
        skill="SQL",
        topic="Querying",
        concept="Aggregation Filtering",
        difficulty="Intermediate"
    )
    q4 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What data structure is standard for SQL indexes?",
        options=["B-Tree", "Linked List", "Binary Heap", "Hash Table"],
        correct_answer="B-Tree",
        explanation="B-Trees balance search, insertion, and deletion efficiency.",
        skill="SQL",
        topic="Indexing",
        concept="B-Tree Index Architecture",
        difficulty="Intermediate"
    )
    # 1 Docker Question
    q5 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Which instruction sets the base image in a Dockerfile?",
        options=["FROM", "RUN", "CMD", "BASE"],
        correct_answer="FROM",
        explanation="FROM initializes a new build stage and sets the base image.",
        skill="Docker",
        topic="Containerization",
        concept="Multi-stage Build Origins",
        difficulty="Intermediate"
    )
    db_session.add_all([q1, q2, q3, q4, q5])
    db_session.commit()

    # 4. Submit Answers:
    # Python: q1 correct, q2 correct -> 2/2 = 100.0%
    # SQL: q3 correct, q4 wrong -> 1/2 = 50.0%
    # Docker: q5 wrong -> 0/1 = 0.0%
    # React: UNTESTED
    submitted_answers = {
        str(q1.id): "A function yielding values",
        str(q2.id): "Global Interpreter Lock",
        str(q3.id): "HAVING",
        str(q4.id): "Linked List",  # Incorrect
        str(q5.id): "CMD"           # Incorrect
    }

    result = AssessmentService.submit_assessment(
        db=db_session,
        user_id=test_user.id,
        assessment_id=assessment.id,
        submitted_answers=submitted_answers
    )

    # 5. Verify Assessment Result Response
    assert result.total_questions == 5
    assert result.correct_count == 3
    assert result.score_percentage == 60.0
    assert result.per_skill_scores is not None
    assert result.per_skill_scores["Python"] == 100.0
    assert result.per_skill_scores["SQL"] == 50.0
    assert result.per_skill_scores["Docker"] == 0.0

    # 6. Verify Direct Persistence in StudentSkill database records
    ss_python = db_session.query(StudentSkill).filter(
        StudentSkill.user_id == test_user.id,
        StudentSkill.skill_id == skill_objs["Python"].id
    ).first()
    assert ss_python.assessment_score == 100.0
    assert ss_python.demonstrated_level == "Advanced"
    assert ss_python.confidence == "High"

    ss_sql = db_session.query(StudentSkill).filter(
        StudentSkill.user_id == test_user.id,
        StudentSkill.skill_id == skill_objs["SQL"].id
    ).first()
    assert ss_sql.assessment_score == 50.0
    assert ss_sql.demonstrated_level == "Beginner"
    assert ss_sql.confidence == "Medium"

    ss_docker = db_session.query(StudentSkill).filter(
        StudentSkill.user_id == test_user.id,
        StudentSkill.skill_id == skill_objs["Docker"].id
    ).first()
    assert ss_docker.assessment_score == 0.0
    assert ss_docker.demonstrated_level == "Beginner"
    assert ss_docker.confidence == "Low"

    # Untested skill (React) strictly remains assessment_score = NULL
    ss_react = db_session.query(StudentSkill).filter(
        StudentSkill.user_id == test_user.id,
        StudentSkill.skill_id == skill_objs["React"].id
    ).first()
    assert ss_react.assessment_score is None
    assert ss_react.confidence == "Low"
    assert ss_react.demonstrated_level is None

    # 7. Verify Skill Matrix reflects updated scores and statuses
    matrix = SkillService.get_skill_matrix(db_session, test_user.id)
    matrix_map = {m.skill_name: m for m in matrix}

    # Python: 100% -> High confidence, Ready
    assert matrix_map["Python"].assessment_score == 100.0
    assert matrix_map["Python"].confidence == "High"
    assert matrix_map["Python"].status == "Ready"

    # SQL: 50% -> Medium confidence, Needs Practice
    assert matrix_map["SQL"].assessment_score == 50.0
    assert matrix_map["SQL"].confidence == "Medium"
    assert matrix_map["SQL"].status == "Needs Practice"

    # Docker: 0% -> Low confidence, Critical Gap
    assert matrix_map["Docker"].assessment_score == 0.0
    assert matrix_map["Docker"].confidence == "Low"
    assert matrix_map["Docker"].status == "Critical Gap"

    # React: Unassessed -> Low confidence, Unassessed (Claim Only)
    assert matrix_map["React"].assessment_score is None
    assert matrix_map["React"].confidence == "Low"
    assert matrix_map["React"].status == "Unassessed (Claim Only)"


def test_retake_preserves_history_and_updates_latest_scores(db_session, test_user, monkeypatch):
    """Verify that retaking an assessment preserves past attempt records in AssessmentAttempt
    and updates StudentSkill with the latest valid score.
    """
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Backend Engineer",
        strengths=["SQL"],
        weaknesses=[],
        skill_gaps=[],
        topics_to_improve=[],
        priority_areas=[],
        improvement_plan=[],
        reassessment_recommendations="Ready",
        summary_feedback="Excellent progress."
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 100, "LIVE_FOUNDRY"))

    sql_sk = db_session.query(Skill).filter(Skill.name == "SQL").first()
    if not sql_sk:
        sql_sk = Skill(name="SQL", category="Database")
        db_session.add(sql_sk)
        db_session.flush()

    ss_sql = db_session.query(StudentSkill).filter(
        StudentSkill.user_id == test_user.id,
        StudentSkill.skill_id == sql_sk.id
    ).first()
    if not ss_sql:
        ss_sql = StudentSkill(
            user_id=test_user.id,
            skill_id=sql_sk.id,
            is_claimed=1,
            confidence="Low",
            assessment_score=None
        )
        db_session.add(ss_sql)
        db_session.commit()

    assessment = Assessment(
        candidate_id=test_user.id,
        title="SQL Targeted Assessment",
        role="Database Developer",
        difficulty="Intermediate",
        question_count=2,
        status="pending",
        questions_json=[]
    )
    db_session.add(assessment)
    db_session.commit()

    q1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What does SQL stand for?",
        options=["Structured Query Language", "Simple Query Language", "Standard Query Logic", "None"],
        correct_answer="Structured Query Language",
        explanation="SQL = Structured Query Language",
        skill="SQL",
        topic="Basics",
        concept="SQL Standard Nomenclature",
        difficulty="Beginner"
    )
    q2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is an ACID transaction?",
        options=["Atomicity Consistency Isolation Durability", "Async Core Index Data", "None", "All"],
        correct_answer="Atomicity Consistency Isolation Durability",
        explanation="ACID guarantees database transactions are processed reliably.",
        skill="SQL",
        topic="Transactions",
        concept="ACID Guarantees",
        difficulty="Intermediate"
    )
    db_session.add_all([q1, q2])
    db_session.commit()

    # Attempt 1: 50% score (1 correct, 1 wrong)
    sub1 = {str(q1.id): "Structured Query Language", str(q2.id): "None"}
    res1 = AssessmentService.submit_assessment(db_session, test_user.id, assessment.id, sub1)
    assert res1.score_percentage == 50.0

    # Verify attempt 1 was saved
    attempts_1 = db_session.query(AssessmentAttempt).filter(
        AssessmentAttempt.user_id == test_user.id,
        AssessmentAttempt.assessment_id == assessment.id
    ).all()
    assert len(attempts_1) == 1

    # StudentSkill should show 50%
    db_session.refresh(ss_sql)
    assert ss_sql.assessment_score == 50.0
    assert ss_sql.confidence == "Medium"

    # Attempt 2 (Retake): 100% score (both correct)
    sub2 = {str(q1.id): "Structured Query Language", str(q2.id): "Atomicity Consistency Isolation Durability"}
    res2 = AssessmentService.submit_assessment(db_session, test_user.id, assessment.id, sub2)
    assert res2.score_percentage == 100.0

    # Verify both attempts are archived in history
    attempts_2 = db_session.query(AssessmentAttempt).filter(
        AssessmentAttempt.user_id == test_user.id,
        AssessmentAttempt.assessment_id == assessment.id
    ).all()
    assert len(attempts_2) == 2

    # StudentSkill should now show 100% and High confidence
    db_session.refresh(ss_sql)
    assert ss_sql.assessment_score == 100.0
    assert ss_sql.confidence == "High"
    assert ss_sql.demonstrated_level == "Advanced"


def test_assessment_concept_column_and_intra_batch_deduplication(db_session, test_user, monkeypatch):
    """Verify that:
    1. Generated questions have concept stored in AssessmentQuestion.
    2. Duplicate concepts within the generated batch are detected and deduplicated.
    """
    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        raw_text="Experienced Python and SQL developer with Docker and FastAPI experience.",
        file_hash="resumehash123",
        version=1
    )
    jd = JobDescription(
        user_id=test_user.id,
        title="Backend Engineer",
        raw_text="Seeking Backend Engineer with strong Python, SQL, and Docker skills.",
        text_hash="jdhash123"
    )
    db_session.add_all([resume, jd])
    db_session.commit()

    # Mock Foundry returning questions with one duplicate concept
    mock_gen_response = AssessmentGenerationResponse(
        title="Personalized Backend Assessment",
        role="Backend Engineer",
        total_questions=3,
        overview="Personalized assessment",
        questions=[
            AssessmentMCQItem(
                id=1,
                question="What is Python GIL?",
                options=["Global Lock", "Local Lock", "No Lock", "Thread Safe"],
                correct_answer="Global Lock",
                explanation="CPython uses a Global Interpreter Lock.",
                skill="Python",
                topic="Concurrency",
                concept="CPython GIL Contention",
                difficulty="Intermediate"
            ),
            AssessmentMCQItem(
                id=2,
                question="How does GIL affect multi-threading?",
                options=["Limits CPU concurrency", "No effect", "Speeds up", "Crashes"],
                correct_answer="Limits CPU concurrency",
                explanation="CPython GIL prevents multiple threads from running bytecode in parallel.",
                skill="Python",
                topic="Concurrency",
                concept="CPython GIL Contention",  # Duplicate concept!
                difficulty="Intermediate"
            ),
            AssessmentMCQItem(
                id=3,
                question="What is Docker volume used for?",
                options=["Persistent storage", "CPU acceleration", "Memory cache", "Network routing"],
                correct_answer="Persistent storage",
                explanation="Volumes persist data generated by containers.",
                skill="Docker",
                topic="Storage",
                concept="Container Data Persistence",
                difficulty="Intermediate"
            )
        ]
    )

    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (mock_gen_response, 150, "LIVE_FOUNDRY"))

    assessment_resp = AssessmentService.generate_personalized_assessment(
        db=db_session,
        user_id=test_user.id,
        role="Backend Engineer",
        num_questions=3
    )

    # Question 2 had the exact duplicate concept as Question 1, so it should be deduplicated
    stored_questions = db_session.query(AssessmentQuestion).filter(
        AssessmentQuestion.assessment_id == assessment_resp.id
    ).all()

    # Verify concept column is populated
    for q in stored_questions:
        assert q.concept is not None
        assert len(q.concept.strip()) > 0

    concepts = [q.concept.lower() for q in stored_questions]
    # No duplicate concepts in stored questions
    assert len(concepts) == len(set(concepts))


def test_api_route_per_skill_result_and_matrix_flow(client, auth_headers, db_session, test_user, monkeypatch):
    """Integration test verifying end-to-end HTTP API behavior:
    1. Submit answers to POST /api/assessments/{id}/submit
    2. Check returned per_skill_scores and status
    3. Call GET /api/assessments/{id}/result (browser refresh scenario)
    4. Call GET /api/skills/matrix to verify persistence across views
    """
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Backend Engineer",
        strengths=["Python"],
        weaknesses=[],
        skill_gaps=[],
        topics_to_improve=[],
        priority_areas=[],
        improvement_plan=[],
        reassessment_recommendations="Great work",
        summary_feedback="All competencies verified."
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_analysis, 100, "LIVE_FOUNDRY"))

    # Get or create skills
    py = db_session.query(Skill).filter(Skill.name == "Python").first()
    if not py:
        py = Skill(name="Python", category="Programming")
        db_session.add(py)
    sql = db_session.query(Skill).filter(Skill.name == "SQL").first()
    if not sql:
        sql = Skill(name="SQL", category="Database")
        db_session.add(sql)
    db_session.flush()

    ss_py = StudentSkill(user_id=test_user.id, skill_id=py.id, is_claimed=1, confidence="Low", assessment_score=None)
    ss_sql = StudentSkill(user_id=test_user.id, skill_id=sql.id, is_claimed=1, confidence="Low", assessment_score=None)
    db_session.add_all([ss_py, ss_sql])
    db_session.commit()

    assessment = Assessment(
        candidate_id=test_user.id,
        title="API Integration Test",
        role="Backend Engineer",
        difficulty="Intermediate",
        question_count=2,
        status="pending",
        questions_json=[]
    )
    db_session.add(assessment)
    db_session.commit()

    q1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Python list comprehension syntax?",
        options=["[x for x in list]", "{x: x}", "(x for x)", "None"],
        correct_answer="[x for x in list]",
        explanation="Standard syntax",
        skill="Python",
        topic="Syntax",
        concept="List Comprehensions",
        difficulty="Beginner"
    )
    q2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="SQL PRIMARY KEY uniqueness?",
        options=["Must be unique and not null", "Can be duplicate", "Nullable", "None"],
        correct_answer="Must be unique and not null",
        explanation="Primary keys enforce entity integrity.",
        skill="SQL",
        topic="Constraints",
        concept="Primary Key Constraints",
        difficulty="Beginner"
    )
    db_session.add_all([q1, q2])
    db_session.commit()

    # 1. Submit via API
    sub_payload = {
        "assessment_id": assessment.id,
        "answers": {
            str(q1.id): "[x for x in list]",
            str(q2.id): "Can be duplicate"  # Incorrect
        }
    }
    submit_res = client.post(f"/api/v1/assessments/{assessment.id}/submit", json=sub_payload, headers=auth_headers)
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["score_percentage"] == 50.0
    assert sub_data["per_skill_scores"]["Python"] == 100.0
    assert sub_data["per_skill_scores"]["SQL"] == 0.0

    # 2. Page refresh simulation: GET /api/v1/assessments/{id}/result
    result_res = client.get(f"/api/v1/assessments/{assessment.id}/result", headers=auth_headers)
    assert result_res.status_code == 200
    res_data = result_res.json()
    assert res_data["per_skill_scores"]["Python"] == 100.0
    assert res_data["per_skill_scores"]["SQL"] == 0.0

    # 3. View Skill Matrix simulation: GET /api/v1/skills/matrix
    matrix_res = client.get("/api/v1/skills/matrix", headers=auth_headers)
    assert matrix_res.status_code == 200
    matrix_data = matrix_res.json()
    matrix_lookup = {item["skill_name"]: item for item in matrix_data}

    assert matrix_lookup["Python"]["assessment_score"] == 100.0
    assert matrix_lookup["Python"]["confidence"] == "High"
    assert matrix_lookup["Python"]["status"] == "Ready"

    assert matrix_lookup["SQL"]["assessment_score"] == 0.0
    assert matrix_lookup["SQL"]["confidence"] == "Low"
    assert matrix_lookup["SQL"]["status"] == "Critical Gap"

