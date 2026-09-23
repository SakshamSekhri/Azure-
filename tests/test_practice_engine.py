import pytest
from backend.app.schemas.ai import (
    AssessmentGenerationResponse,
    AssessmentMCQItem,
    AssessmentResultAnalysisResponse
)
from backend.app.ai.foundry_agent import foundry_client
from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.models.job import JobDescription
from backend.app.services.skill_topic_service import SkillTopicService
from backend.app.services.skill_service import SkillService
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.core.security import hash_password


def _make_dummy_mcq(skill: str, topic: str, concept: str, q_num: int) -> AssessmentMCQItem:
    return AssessmentMCQItem(
        id=q_num,
        question=f"Which configuration directive is recommended in {skill} for {topic} issue #{q_num}?",
        options=[
            f"Use the standard {skill} {concept} flag",
            f"Disable the {skill} background daemon",
            f"Set default timeout to infinite in {topic}",
            f"Run as privileged superuser without isolation"
        ],
        correct_answer=f"Use the standard {skill} {concept} flag",
        explanation=f"Using the standard flag properly isolates {concept} in {skill}.",
        skill=skill,
        topic=topic,
        concept=concept,
        difficulty="Intermediate",
        why_the_question_is_relevant=f"Tests core operational knowledge of {skill} {topic}."
    )


def test_practice_generation_success(client, auth_headers, test_user, monkeypatch):
    """Test generating a 5-question practice session for a skill."""
    dummy_questions = [
        _make_dummy_mcq("Docker", "Container Networking", f"Concept_{i}", i)
        for i in range(1, 6)
    ]
    dummy_response = AssessmentGenerationResponse(
        title="Practice: Docker — Container Networking",
        role="Docker",
        overview="5 focused questions on Docker networking",
        total_questions=5,
        questions=dummy_questions
    )

    monkeypatch.setattr(
        foundry_client,
        "execute_operation",
        lambda *args, **kwargs: (dummy_response, 120, "LIVE_FOUNDRY")
    )

    res = client.post("/api/v1/practice/generate", headers=auth_headers, json={
        "skill": "Docker",
        "topic": "Container Networking",
        "num_questions": 5
    })

    assert res.status_code == 200
    data = res.json()
    assert data["assessment_mode"] == "practice"
    assert data["role"] == "Docker"
    assert data["topic"] == "Container Networking"
    assert data["total_questions"] == 5
    assert len(data["questions"]) == 5

    # Check question options and fields
    for q in data["questions"]:
        assert len(q["options"]) == 4
        assert q["skill"] == "Docker"
        assert "question" in q


def test_practice_generation_adaptive_difficulty(db_session, test_user):
    """Test adaptive difficulty calculation based on history."""
    # 1. Unassessed gap -> Beginner
    diff_gap = SkillTopicService.compute_adaptive_difficulty(db_session, test_user.id, "kubernetes", "Ingress")
    assert diff_gap == "Beginner"

    # 2. Claimed skill without answers -> Intermediate
    k8s = Skill(canonical_id="kubernetes", name="Kubernetes", category="DevOps")
    db_session.add(k8s)
    db_session.flush()
    sk = StudentSkill(user_id=test_user.id, skill_id=k8s.id, is_claimed=True)
    db_session.add(sk)
    db_session.commit()

    diff_claimed = SkillTopicService.compute_adaptive_difficulty(db_session, test_user.id, "kubernetes", "Ingress")
    assert diff_claimed == "Intermediate"

    # 3. High past score (85%) -> Advanced
    sk.assessment_score = 85.0
    db_session.commit()
    diff_high = SkillTopicService.compute_adaptive_difficulty(db_session, test_user.id, "kubernetes", "Ingress")
    assert diff_high == "Advanced"


def test_skill_focus_detail_and_dynamic_topics(client, auth_headers, test_user):
    """Test retrieving skill focus details and dynamic topic aggregation."""
    res = client.get("/api/v1/practice/skills/python/focus", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["skill_name"] == "Python"
    assert data["canonical_id"] == "python"
    assert "topics" in data
    assert len(data["topics"]) > 0
    assert "recommended_action" in data
    assert data["recommended_action"]["action_type"] in ("PRACTICE", "FOCUSED_ASSESSMENT")


def test_practice_submission_deterministic_scoring(client, auth_headers, test_user, db_session, monkeypatch):
    """Test deterministic scoring and results of practice session."""
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Docker",
        strengths=["Container Networking"],
        weaknesses=[],
        skill_gaps=[],
        topics_to_improve=[],
        priority_areas=["Production Security"],
        improvement_plan=["Review iptables networking"],
        reassessment_recommendations="Ready for focused assessment",
        summary_feedback="Excellent score."
    )
    monkeypatch.setattr(
        foundry_client,
        "execute_operation",
        lambda *args, **kwargs: (dummy_analysis, 100, "LIVE_FOUNDRY")
    )

    assessment = Assessment(
        candidate_id=test_user.id,
        title="Practice: Docker — Container Networking",
        role="Docker",
        difficulty="Intermediate",
        question_count=2,
        status="pending",
        assessment_mode="practice",
        topic="Container Networking",
        canonical_skill_id="docker"
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    q1 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="Which Docker network driver enables container multi-host communication?",
        options=["bridge", "host", "overlay", "macvlan"],
        correct_answer="overlay",
        explanation="The overlay network driver creates a distributed network across multiple Docker daemon hosts.",
        skill="Docker",
        topic="Container Networking",
        concept="Overlay Driver",
        difficulty="Intermediate"
    )
    q2 = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is the default Docker network driver for standalone containers?",
        options=["bridge", "overlay", "none", "macvlan"],
        correct_answer="bridge",
        explanation="Default network driver is bridge.",
        skill="Docker",
        topic="Container Networking",
        concept="Bridge Driver",
        difficulty="Intermediate"
    )
    db_session.add_all([q1, q2])
    db_session.commit()
    db_session.refresh(q1)
    db_session.refresh(q2)

    # Submit 1 correct, 1 incorrect
    submission = {
        "assessment_id": assessment.id,
        "answers": {
            str(q1.id): "overlay",  # Correct
            str(q2.id): "none"       # Incorrect
        }
    }
    submit_res = client.post(f"/api/v1/assessments/{assessment.id}/submit", headers=auth_headers, json=submission)
    assert submit_res.status_code == 200
    res_data = submit_res.json()
    assert res_data["score_percentage"] == 50.0
    assert res_data["correct_count"] == 1
    assert res_data["total_questions"] == 2
    assert res_data["assessment_mode"] == "practice"
    assert res_data["topic"] == "Container Networking"
    assert len(res_data["details"]) == 2


def test_practice_authorization_isolation(client, db_session, test_user):
    """Ensure User B cannot view or submit User A's practice session."""
    user_b = User(
        email="user_b@example.com",
        password_hash=hash_password("password123"),
        is_active=True
    )
    db_session.add(user_b)
    db_session.commit()
    token_b = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A assessment
    assessment_a = Assessment(
        candidate_id=test_user.id,
        title="User A Practice",
        role="Python",
        difficulty="Beginner",
        question_count=1,
        status="pending",
        assessment_mode="practice"
    )
    db_session.add(assessment_a)
    db_session.commit()
    db_session.refresh(assessment_a)

    # User B tries to fetch User A's assessment
    get_res = client.get(f"/api/v1/assessments/{assessment_a.id}", headers=headers_b)
    assert get_res.status_code == 404

    # User B tries to submit User A's assessment
    sub_res = client.post(f"/api/v1/assessments/{assessment_a.id}/submit", headers=headers_b, json={
        "assessment_id": assessment_a.id,
        "answers": {"1": "opt"}
    })
    assert sub_res.status_code in (403, 404)


def test_focused_assessment_generation(client, auth_headers, monkeypatch):
    """Test generating a 10-question focused assessment."""
    dummy_questions = [
        _make_dummy_mcq("FastAPI", "Dependency Injection", f"Concept_{i}", i)
        for i in range(1, 11)
    ]
    dummy_response = AssessmentGenerationResponse(
        title="Focused Assessment: FastAPI — Dependency Injection",
        role="FastAPI",
        overview="Comprehensive evaluation on dependency injection",
        total_questions=10,
        questions=dummy_questions
    )

    monkeypatch.setattr(
        foundry_client,
        "execute_operation",
        lambda *args, **kwargs: (dummy_response, 200, "LIVE_FOUNDRY")
    )

    res = client.post("/api/v1/practice/focused-assessment/generate", headers=auth_headers, json={
        "skill": "FastAPI",
        "topic": "Dependency Injection",
        "num_questions": 10
    })

    assert res.status_code == 200
    data = res.json()
    assert data["assessment_mode"] == "focused_assessment"
    assert data["role"] == "FastAPI"
    assert data["total_questions"] == 10


def test_dashboard_recommendation_prioritizes_practice(db_session, test_user):
    """Verify recommendation engine suggests practice on critical JD gaps."""
    # Ensure test_user has at least one tracked skill
    py_skill = db_session.query(Skill).filter(Skill.name == "Python").first()
    student_skill = StudentSkill(user_id=test_user.id, skill_id=py_skill.id, is_claimed=True)
    db_session.add(student_skill)
    db_session.flush()

    # Create JD requiring Docker (which candidate does not have -> Critical Gap)
    jd = JobDescription(
        user_id=test_user.id,
        title="Backend Engineer",
        raw_text="Required: Docker, Python",
        text_hash="abc_docker_hash",
        parsed_data={
            "required_skills": [{"name": "Docker", "category": "DevOps"}],
            "preferred_skills": []
        }
    )
    db_session.add(jd)
    db_session.commit()

    rec = SkillService.get_recommended_next_action(db_session, test_user.id)
    assert rec.action_type == "PRACTICE"
    assert rec.skill_name == "Docker"
    assert rec.target_route == "🎯 Skill & Topic Practice"


def test_skill_focus_and_topics_with_slashes_and_special_chars(client, auth_headers):
    """Verify that skills containing slashes or special characters (like 'SEO / SEM', 'CI/CD', 'C++', 'C#')
    never produce 404 Not Found errors and return valid focus and topics data.
    """
    special_skills = ["SEO / SEM", "CI/CD", "C++", "C#"]

    for skill in special_skills:
        # Test query parameter endpoint
        res_focus = client.get("/api/v1/practice/skills/focus", headers=auth_headers, params={"skill": skill})
        assert res_focus.status_code == 200, f"Failed for {skill}: {res_focus.text}"
        data_focus = res_focus.json()
        assert "skill_name" in data_focus
        assert len(data_focus.get("topic_breakdown", [])) > 0

        res_topics = client.get("/api/v1/practice/skills/topics", headers=auth_headers, params={"skill": skill})
        assert res_topics.status_code == 200, f"Failed for {skill}: {res_topics.text}"
        data_topics = res_topics.json()
        assert isinstance(data_topics, list)
        assert len(data_topics) > 0

        # Test path parameter endpoint (with :path converter and proper URL encoding for fragments like #)
        import urllib.parse
        encoded_skill = urllib.parse.quote(skill, safe='')
        res_path = client.get(f"/api/v1/practice/skills/{encoded_skill}/focus", headers=auth_headers)
        assert res_path.status_code == 200, f"Path failed for {skill}: {res_path.text}"
