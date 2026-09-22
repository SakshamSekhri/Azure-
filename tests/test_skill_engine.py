from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.evidence import Evidence
from backend.app.services.skill_service import SkillService


def test_skill_gap_engine_deterministic_matrix(db_session, test_user):
    py_skill = db_session.query(Skill).filter(Skill.name == "Python").first()
    sql_skill = db_session.query(Skill).filter(Skill.name == "SQL").first()

    # Student has Python with assessment 85% and GitHub evidence
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=py_skill.id,
        is_claimed=1,
        assessment_score=85.0,
        confidence="High"
    ))
    db_session.add(Evidence(
        user_id=test_user.id,
        skill_id=py_skill.id,
        type="GitHub",
        source="github.com/test/repo",
        title="Python Repo",
        evidence_strength=0.7
    ))

    # Student has SQL with assessment 42% and no GitHub evidence
    db_session.add(StudentSkill(
        user_id=test_user.id,
        skill_id=sql_skill.id,
        is_claimed=1,
        assessment_score=42.0,
        confidence="Low"
    ))
    db_session.commit()

    matrix = SkillService.get_skill_matrix(db_session, test_user.id)
    assert len(matrix) == 2

    py_item = next(m for m in matrix if m.skill_name == "Python")
    sql_item = next(m for m in matrix if m.skill_name == "SQL")

    assert py_item.confidence == "High"
    assert py_item.status == "Ready"
    assert py_item.github_evidence is True

    assert sql_item.confidence == "Low"
    assert sql_item.status == "Critical Gap"
    assert sql_item.github_evidence is False

    # Check recommended action: should target SQL gap
    action = SkillService.get_recommended_next_action(db_session, test_user.id)
    assert "SQL" in action.title or action.action_type in ["LEARNING", "ASSESSMENT"]
