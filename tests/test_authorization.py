import pytest
from backend.app.core.security import hash_password, create_access_token
from backend.app.models.user import User
from backend.app.models.profile import StudentProfile
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.learning_plan import LearningPlan
from backend.app.models.learning_activity import LearningActivity


@pytest.fixture
def second_user(db_session):
    user = User(
        email="attacker@example.com",
        password_hash=hash_password("attackerpassword123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = StudentProfile(
        user_id=user.id,
        name="Attacker Student",
        target_role="Data Scientist"
    )
    db_session.add(profile)
    db_session.commit()
    return user


@pytest.fixture
def second_user_headers(second_user):
    token = create_access_token(subject=second_user.id)
    return {"Authorization": f"Bearer {token}"}


def test_user_cannot_access_other_users_assessment(client, db_session, test_user, second_user_headers, auth_headers):
    # Create assessment owned by test_user
    assessment = Assessment(
        candidate_id=test_user.id,
        title="Owner Assessment",
        role="Backend Engineer",
        difficulty="Intermediate",
        question_count=1,
        status="pending"
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    # Owner can access it
    res_owner = client.get(f"/api/v1/assessments/{assessment.id}", headers=auth_headers)
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == assessment.id

    # Second user cannot access it -> 404
    res_attacker = client.get(f"/api/v1/assessments/{assessment.id}", headers=second_user_headers)
    assert res_attacker.status_code == 404
    assert "Assessment not found" in res_attacker.json()["detail"]


def test_user_cannot_submit_other_users_assessment(client, db_session, test_user, second_user_headers):
    assessment = Assessment(
        candidate_id=test_user.id,
        title="Owner Assessment 2",
        role="Backend Engineer",
        difficulty="Intermediate",
        question_count=1,
        status="pending"
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    q = AssessmentQuestion(
        assessment_id=assessment.id,
        question="What is Python programming language?",
        options=["Language", "Snake", "Both", "None"],
        correct_answer="Both",
        explanation="Multi-paradigm language and a reptile",
        skill="Python",
        difficulty="Beginner"
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)

    payload = {
        "assessment_id": assessment.id,
        "answers": {str(q.id): "Both"}
    }
    res = client.post(f"/api/v1/assessments/{assessment.id}/submit", json=payload, headers=second_user_headers)
    assert res.status_code == 404
    assert "Assessment not found" in res.json()["detail"]


def test_user_cannot_view_other_users_assessment_result(client, db_session, test_user, second_user_headers, auth_headers):
    assessment = Assessment(
        candidate_id=test_user.id,
        title="Completed Assessment",
        role="Backend Engineer",
        difficulty="Intermediate",
        question_count=1,
        status="completed"
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        user_id=test_user.id,
        score_percentage=100.0,
        correct_count=1,
        total_questions=1,
        answers_json={},
        attempt_number=1
    )
    db_session.add(attempt)
    db_session.commit()

    # Owner can access result
    res_owner = client.get(f"/api/v1/assessments/{assessment.id}/result", headers=auth_headers)
    assert res_owner.status_code == 200
    assert res_owner.json()["score_percentage"] == 100.0

    # Second user cannot access result
    res_attacker = client.get(f"/api/v1/assessments/{assessment.id}/result", headers=second_user_headers)
    assert res_attacker.status_code == 404


def test_user_cannot_view_other_users_resume(client, db_session, test_user, second_user_headers, auth_headers):
    resume = Resume(
        user_id=test_user.id,
        filename="confidential_resume.pdf",
        raw_text="Secret confidential candidate resume data",
        file_hash="hash12345"
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    # Owner can view resume
    res_owner = client.get(f"/api/v1/resume/{resume.id}", headers=auth_headers)
    assert res_owner.status_code == 200
    assert res_owner.json()["filename"] == "confidential_resume.pdf"

    # Second user cannot view resume
    res_attacker = client.get(f"/api/v1/resume/{resume.id}", headers=second_user_headers)
    assert res_attacker.status_code == 404
    assert "Resume not found" in res_attacker.json()["detail"]


def test_user_cannot_view_other_users_job_description(client, db_session, test_user, second_user_headers, auth_headers):
    job = JobDescription(
        user_id=test_user.id,
        title="Confidential Lead Architect",
        company="Stealth Startup",
        raw_text="Job description confidential content",
        text_hash="hash5678"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Owner can view job
    res_owner = client.get(f"/api/v1/jobs/{job.id}", headers=auth_headers)
    assert res_owner.status_code == 200
    assert res_owner.json()["title"] == "Confidential Lead Architect"

    # Second user cannot view job
    res_attacker = client.get(f"/api/v1/jobs/{job.id}", headers=second_user_headers)
    assert res_attacker.status_code == 404
    assert "Job description not found" in res_attacker.json()["detail"]


def test_user_cannot_view_or_toggle_other_users_learning_plan(client, db_session, test_user, second_user_headers, auth_headers):
    plan = LearningPlan(
        user_id=test_user.id,
        target_role="Backend Engineer",
        duration_days=7,
        status="active",
        summary="Plan overview"
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    activity = LearningActivity(
        plan_id=plan.id,
        day_number=1,
        topic="Read Python internals",
        skill_name="Python",
        completed=False
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    # Owner can view plan
    res_owner = client.get(f"/api/v1/learning/plan/{plan.id}", headers=auth_headers)
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == plan.id

    # Second user cannot view plan
    res_attacker = client.get(f"/api/v1/learning/plan/{plan.id}", headers=second_user_headers)
    assert res_attacker.status_code == 404
    assert "Learning plan not found" in res_attacker.json()["detail"]

    # Second user cannot toggle activity
    res_toggle = client.post(
        "/api/v1/learning/activity/toggle",
        json={"activity_id": activity.id, "completed": True},
        headers=second_user_headers
    )
    assert res_toggle.status_code == 404
    assert "not found" in res_toggle.json()["detail"].lower()

    # Owner CAN toggle activity
    res_toggle_owner = client.post(
        "/api/v1/learning/activity/toggle",
        json={"activity_id": activity.id, "completed": True},
        headers=auth_headers
    )
    assert res_toggle_owner.status_code == 200
    assert res_toggle_owner.json()["completed"] is True
