from backend.app.services.learning_service import LearningService
from backend.app.models.skill import Skill, StudentSkill


def test_learning_plan_generation_and_activity_toggle(db_session, test_user):
    # Setup weak skills
    py_skill = db_session.query(Skill).filter(Skill.name == "Python").first()
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=py_skill.id,
        is_claimed=1,
        assessment_score=40.0,
        confidence="Low"
    ))
    db_session.commit()

    # Generate 7-Day Plan
    plan = LearningService.generate_7day_plan(
        db=db_session,
        user_id=test_user.id,
        target_role="Backend Developer",
        force_refresh=True
    )

    assert plan.id is not None
    assert plan.duration_days == 7
    assert len(plan.activities) == 7
    assert plan.completion_percentage == 0.0

    # Toggle Day 1 as completed
    act_1 = plan.activities[0]
    updated_act = LearningService.toggle_activity(
        db=db_session,
        user_id=test_user.id,
        activity_id=act_1.id,
        completed=True
    )
    assert updated_act.completed is True

    # Re-fetch plan and check percentage
    current_plan = LearningService.get_current_plan(db_session, test_user.id)
    assert current_plan.completion_percentage > 0.0


def test_dynamic_improvement_plan_service(db_session, test_user):
    # Setup skills with various scores
    py_skill = db_session.query(Skill).filter(Skill.name == "Python").first()
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=py_skill.id,
        is_claimed=1,
        assessment_score=40.0,
        confidence="Low"
    ))
    db_session.commit()

    # Generate dynamic improvement plan
    plan_resp = LearningService.get_dynamic_improvement_plan(db_session, test_user.id)
    assert plan_resp is not None
    assert len(plan_resp.items) > 0
    assert plan_resp.high_priority_count >= 1

    # Check the Python item
    py_item = next((it for it in plan_resp.items if it.skill_name.lower() == "python"), None)
    assert py_item is not None
    assert py_item.current_score == 40.0
    assert py_item.target_score == 80.0
    assert py_item.priority == "HIGH"
    assert py_item.status == "In Progress"
    assert "learn" in py_item.actions
    assert "practice" in py_item.actions
    assert "assess" in py_item.actions

    # Dynamic adaptation: update score to >= 80.0% and verify it transitions to Mastered
    ss = db_session.query(StudentSkill).filter(
        StudentSkill.user_id == test_user.id,
        StudentSkill.skill_id == py_skill.id
    ).first()
    ss.assessment_score = 85.0
    ss.confidence = "High"
    db_session.commit()

    updated_plan = LearningService.get_dynamic_improvement_plan(db_session, test_user.id)
    updated_py = next((it for it in updated_plan.items if it.skill_name.lower() == "python"), None)
    assert updated_py is not None
    assert updated_py.status == "Mastered"
    assert updated_py.current_score == 85.0
    assert updated_plan.mastered_count >= 1


def test_improvement_plan_endpoint(client, auth_headers):
    res = client.get("/api/v1/learning/improvement-plan", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "high_priority_count" in data
    assert "medium_priority_count" in data
    assert "low_priority_count" in data
    assert "mastered_count" in data
    assert "target_role" in data
