from backend.app.core.database import Base
from backend.app.models.user import User
from backend.app.models.profile import StudentProfile
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.evidence import Evidence
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.learning_plan import LearningPlan
from backend.app.models.learning_activity import LearningActivity
from backend.app.models.feedback import Feedback
from backend.app.models.ai_operation import AIOperation

__all__ = [
    "Base",
    "User",
    "StudentProfile",
    "Resume",
    "JobDescription",
    "Skill",
    "StudentSkill",
    "Evidence",
    "Assessment",
    "AssessmentQuestion",
    "AssessmentAnswer",
    "AssessmentAttempt",
    "LearningPlan",
    "LearningActivity",
    "Feedback",
    "AIOperation"
]
