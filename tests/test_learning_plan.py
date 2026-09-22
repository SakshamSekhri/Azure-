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
