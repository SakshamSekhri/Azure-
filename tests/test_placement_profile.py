import pytest
from backend.app.services.placement_profile_service import PlacementProfileService
from backend.app.models.profile import StudentProfile
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.services.skill_service import SkillService
from backend.app.models.skill import StudentSkill


def test_placement_profile_aggregation(db_session, test_user):
    # Set up resume with projects, experience, skills
    resume = Resume(
        user_id=test_user.id,
        filename="alice_resume.pdf",
        raw_text="Python and FastAPI developer with cloud experience",
        file_hash="res_alice_123",
        parsed_data={
            "skills": [
                {"name": "Python", "category": "Backend"},
                {"name": "FastAPI", "category": "Backend"}
            ],
            "projects": [
                {"name": "Microservices API", "description": "High-scale API gateway", "tech_stack": ["FastAPI", "Redis"]}
            ],
            "experience": ["Backend Intern at TechCorp (6 months)"],
            "education": ["B.Tech Computer Science"],
            "certifications": ["AWS Cloud Practitioner"]
        }
    )
    db_session.add(resume)

    # Set up job with requirements
    job = JobDescription(
        user_id=test_user.id,
        title="Senior Python Backend Developer",
        raw_text="Seeking Senior Python Backend Developer with Docker and PostgreSQL expertise",
        text_hash="job_alice_123",
        parsed_data={
            "required_skills": [
                {"name": "Python", "category": "Backend"},
                {"name": "Docker", "category": "DevOps"},
                {"name": "PostgreSQL", "category": "Database"}
            ],
            "preferred_skills": [
                {"name": "Kubernetes", "category": "DevOps"}
            ]
        }
    )
    db_session.add(job)

    # Also register candidate claimed skills in student_skills table
    s_py = SkillService.get_or_create_skill(db_session, "Python", "Programming")
    s_fast = SkillService.get_or_create_skill(db_session, "FastAPI", "Framework")
    db_session.add_all([
        StudentSkill(user_id=test_user.id, skill_id=s_py.id, is_claimed=1),
        StudentSkill(user_id=test_user.id, skill_id=s_fast.id, is_claimed=1)
    ])

    # Set up an assessment with 1 incorrect answer to test weak topic extraction
    assessment = Assessment(
        candidate_id=test_user.id,
        title="Docker Basics",
        role="Senior Python Backend Developer",
        difficulty="Intermediate",
        question_count=2,
        status="completed"
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    q1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is the difference between ADD and COPY in Dockerfile?",
        options=["ADD can extract tar archives", "COPY can extract tar archives", "They are identical", "None"],
        correct_answer="ADD can extract tar archives",
        explanation="ADD has tar auto-extraction capabilities.",
        skill="Docker",
        canonical_skill_id="docker",
        topic="Dockerfile Directives",
        difficulty="Intermediate"
    )
    q2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Which flag runs a Docker container in detached mode?",
        options=["-d", "-i", "-t", "-p"],
        correct_answer="-d",
        explanation="-d flag specifies detached mode.",
        skill="Docker",
        canonical_skill_id="docker",
        topic="CLI Commands",
        difficulty="Beginner"
    )
    db_session.add_all([q1, q2])
    db_session.commit()
    db_session.refresh(q1)
    db_session.refresh(q2)

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        user_id=test_user.id,
        score_percentage=50.0,
        correct_count=1,
        total_questions=2,
        answers_json={
            str(q1.id): "They are identical",  # Incorrect answer -> triggers weak topic
            str(q2.id): "-d"                   # Correct answer
        },
        attempt_number=1
    )
    db_session.add(attempt)
    db_session.add_all([
        AssessmentAnswer(
            assessment_id=assessment.id,
            question_id=q1.id,
            candidate_id=test_user.id,
            selected_answer="They are identical",
            correct_answer="ADD can extract tar archives",
            is_correct=False
        ),
        AssessmentAnswer(
            assessment_id=assessment.id,
            question_id=q2.id,
            candidate_id=test_user.id,
            selected_answer="-d",
            correct_answer="-d",
            is_correct=True
        )
    ])
    db_session.commit()

    # Get placement profile
    profile = PlacementProfileService.get_placement_profile(db_session, test_user.id)

    assert profile.candidate.user_id == test_user.id
    assert profile.candidate.target_role == "Full Stack Developer" or profile.candidate.target_role is not None

    # Claimed skills
    claimed_ids = [s.canonical_id for s in profile.claimed_skills]
    assert "python" in claimed_ids
    assert "fastapi" in claimed_ids

    # Required skills
    req_ids = [s.canonical_id for s in profile.required_skills]
    assert "python" in req_ids
    assert "docker" in req_ids
    assert "postgresql" in req_ids

    # Skill gaps (Docker and PostgreSQL missing from claimed skills)
    gap_ids = [g.canonical_id for g in profile.skill_gaps]
    assert "docker" in gap_ids
    assert "postgresql" in gap_ids

    # Weak topics extracted from incorrect answer
    assert any("Dockerfile Directives" in wt or "docker" in wt.lower() for wt in profile.weak_topics)

    # Projects and experience
    assert len(profile.projects) == 1
    assert profile.projects[0]["name"] == "Microservices API"


def test_build_compact_ai_context(db_session, test_user):
    profile = PlacementProfileService.get_placement_profile(db_session, test_user.id)
    compact_ctx = PlacementProfileService.build_compact_ai_context(profile, num_questions=5)

    assert isinstance(compact_ctx, dict)
    assert "target_role" in compact_ctx
    assert "required_skills" in compact_ctx
    assert "skill_gaps" in compact_ctx
    assert "claimed_skills" in compact_ctx
    assert compact_ctx["num_questions"] == 5


def test_placement_profile_api_endpoint(client, auth_headers):
    res = client.get("/api/v1/profile/placement-profile", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "candidate" in data
    assert "claimed_skills" in data
    assert "verified_skills" in data
    assert "required_skills" in data
    assert "skill_gaps" in data
    assert "weak_topics" in data
    assert "assessment_history" in data
    assert data["candidate"]["user_id"] is not None
