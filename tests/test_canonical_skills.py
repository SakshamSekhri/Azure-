import pytest
from backend.app.services.skill_canonicalizer import canonicalize_skill
from backend.app.services.skill_service import SkillService
from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.evidence import Evidence
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_answer import AssessmentAnswer


def test_canonicalize_known_skills():
    cases = [
        ("React.js", "react", "React", "Frontend"),
        ("reactjs", "react", "React", "Frontend"),
        ("React", "react", "React", "Frontend"),
        ("PostgreSQL", "postgresql", "PostgreSQL", "Database"),
        ("postgres", "postgresql", "PostgreSQL", "Database"),
        ("Node.js", "nodejs", "Node.js", "Framework"),
        ("node js", "nodejs", "Node.js", "Framework"),
        ("k8s", "kubernetes", "Kubernetes", "DevOps"),
        ("Kubernetes", "kubernetes", "Kubernetes", "DevOps"),
        ("FastAPI", "fastapi", "FastAPI", "Framework"),
        ("fast api", "fastapi", "FastAPI", "Framework"),
        ("ml", "machine-learning", "Machine Learning", "AI/ML"),
        ("OOP", "oop", "Object-Oriented Programming", "CS Fundamentals"),
    ]
    for raw_name, expected_id, expected_display, expected_category in cases:
        canon = canonicalize_skill(raw_name)
        assert canon.canonical_id == expected_id, f"Failed for raw: {raw_name}"
        assert canon.display_name == expected_display, f"Display name mismatch for raw: {raw_name}"
        assert canon.category == expected_category, f"Category mismatch for raw: {raw_name}"


def test_canonicalize_unknown_skill_slug():
    canon = canonicalize_skill("My Custom In-House Framework v3.0")
    assert canon.canonical_id == "my-custom-in-house-framework-v3-0"
    assert canon.display_name == "My Custom In-house Framework V3.0"
    assert canon.category == "Technical"


def test_get_or_create_skill_deduplication(db_session):
    # First creation with alias 'React.js'
    s1 = SkillService.get_or_create_skill(db_session, "React.js", "Frontend")
    assert s1.canonical_id == "react"
    assert s1.name == "React"

    # Second call with alias 'reactjs'
    s2 = SkillService.get_or_create_skill(db_session, "reactjs", "Frontend")
    assert s2.id == s1.id
    assert s2.canonical_id == "react"


def test_compare_candidate_vs_jd_canonical_matching(db_session, test_user):
    s_react = SkillService.get_or_create_skill(db_session, "React.js", "Frontend")
    s_pg = SkillService.get_or_create_skill(db_session, "PostgreSQL", "Database")

    # Add claimed skills to StudentSkill
    db_session.add_all([
        StudentSkill(user_id=test_user.id, skill_id=s_react.id, is_claimed=1),
        StudentSkill(user_id=test_user.id, skill_id=s_pg.id, is_claimed=1)
    ])

    # Candidate has React.js and PostgreSQL in Resume
    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        raw_text="Experienced with React.js and PostgreSQL database systems",
        file_hash="res123",
        parsed_data={
            "skills": [
                {"name": "React.js", "category": "Frontend"},
                {"name": "PostgreSQL", "category": "Database"}
            ]
        }
    )
    # JD requires React, Postgres, and Docker
    job = JobDescription(
        user_id=test_user.id,
        title="Fullstack Engineer",
        raw_text="Seeking Fullstack Engineer with React, postgres, and Docker expertise",
        text_hash="job123",
        parsed_data={
            "required_skills": [
                {"name": "React", "category": "Frontend"},
                {"name": "postgres", "category": "Database"},
                {"name": "Docker", "category": "DevOps"}
            ],
            "preferred_skills": []
        }
    )
    db_session.add_all([resume, job])
    db_session.commit()

    comparison = SkillService.compare_candidate_vs_jd(db_session, test_user.id)

    # Both React and PostgreSQL should be matched as needing assessment rather than being missing gaps
    assert "React" in comparison.needs_assessment or "react" in comparison.needs_assessment
    assert "postgres" in comparison.needs_assessment or "PostgreSQL" in comparison.needs_assessment

    # Docker was never claimed by the candidate, so it is a critical skill gap
    assert "Docker" in comparison.skill_gaps or "docker" in comparison.skill_gaps


def test_multi_source_evidence_confidence_calibration(db_session, test_user):
    py_skill = SkillService.get_or_create_skill(db_session, "Python", "Programming")
    sql_skill = SkillService.get_or_create_skill(db_session, "SQL", "Database")
    docker_skill = SkillService.get_or_create_skill(db_session, "Docker", "DevOps")
    redis_skill = SkillService.get_or_create_skill(db_session, "Redis", "Database")

    assessment = Assessment(
        candidate_id=test_user.id,
        title="Diagnostic Test",
        role="Backend Engineer",
        difficulty="Intermediate",
        question_count=3,
        status="completed"
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    # 1. Candidate claims Python on resume only -> Low confidence (Unassessed Claim Only)
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=py_skill.id,
        is_claimed=1
    ))

    # 2. Candidate has SQL with high assessment score (90%) but only 1 question (<2 sample threshold) -> Capped at Medium
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=sql_skill.id,
        is_claimed=0,
        assessment_score=90.0
    ))
    q_sql = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is an SQL JOIN operation?",
        options=["Combine rows from tables", "Drop table from database", "Insert single row", "Rollback transaction"],
        correct_answer="Combine rows from tables",
        explanation="JOIN combines rows based on common keys.",
        skill="SQL",
        canonical_skill_id="sql",
        difficulty="Beginner"
    )
    db_session.add(q_sql)
    db_session.commit()
    db_session.add(AssessmentAnswer(
        assessment_id=assessment.id,
        question_id=q_sql.id,
        candidate_id=test_user.id,
        selected_answer="Combine rows from tables",
        correct_answer="Combine rows from tables",
        is_correct=True
    ))

    # 3. Candidate has Docker with high assessment score (85%) and 2 questions -> High confidence, Ready
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=docker_skill.id,
        is_claimed=1,
        assessment_score=85.0
    ))
    q_d1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is Docker image layering concept?",
        options=["Read-only image layers", "Single binary file", "Shared RAM disk", "Virtual network bridge"],
        correct_answer="Read-only image layers",
        explanation="Docker images are composed of immutable layers.",
        skill="Docker",
        canonical_skill_id="docker",
        difficulty="Intermediate"
    )
    q_d2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Which CLI command runs a Docker container in detached background mode?",
        options=["docker run -d", "docker stop -f", "docker build -t", "docker push -a"],
        correct_answer="docker run -d",
        explanation="docker run -d runs container in background.",
        skill="Docker",
        canonical_skill_id="docker",
        difficulty="Beginner"
    )
    db_session.add_all([q_d1, q_d2])
    db_session.commit()
    db_session.add_all([
        AssessmentAnswer(assessment_id=assessment.id, question_id=q_d1.id, candidate_id=test_user.id, selected_answer="Read-only image layers", correct_answer="Read-only image layers", is_correct=True),
        AssessmentAnswer(assessment_id=assessment.id, question_id=q_d2.id, candidate_id=test_user.id, selected_answer="docker run -d", correct_answer="docker run -d", is_correct=True)
    ])

    # 4. Candidate has Redis with low assessment score (40%) -> Low confidence, Critical Gap
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=redis_skill.id,
        is_claimed=1,
        assessment_score=40.0
    ))
    db_session.commit()

    matrix = SkillService.get_skill_matrix(db_session, test_user.id)
    matrix_map = {item.skill_name: item for item in matrix}

    # Verify Docker: High confidence, Ready
    assert matrix_map["Docker"].confidence == "High"
    assert matrix_map["Docker"].status == "Ready"

    # Verify SQL: Capped at Medium due to small sample size (<2 questions)
    assert matrix_map["SQL"].confidence == "Medium"
    assert matrix_map["SQL"].status == "Needs Practice"

    # Verify Redis: Low confidence, Critical Gap
    assert matrix_map["Redis"].confidence == "Low"
    assert matrix_map["Redis"].status == "Critical Gap"

    # Verify Python: Low confidence, Unassessed (Claim Only)
    assert matrix_map["Python"].confidence == "Low"
    assert matrix_map["Python"].status == "Unassessed (Claim Only)"
