from backend.app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from backend.app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from backend.app.schemas.resume import ResumeResponse, ResumeAnalysisRequest
from backend.app.schemas.job import JobDescriptionCreate, JobDescriptionResponse, JobAnalysisRequest
from backend.app.schemas.skill import (
    SkillCreate, SkillResponse, StudentSkillResponse, SkillMatrixItem,
    SkillGapResponse, RecommendedActionResponse, CandidateJDSkillItem, CandidateJDComparisonResponse
)
from backend.app.schemas.evidence import EvidenceCreate, EvidenceResponse
from backend.app.schemas.github import GitHubConnectRequest, GitHubRepoInfo, GitHubAnalysisResponse
from backend.app.schemas.assessment import (
    AssessmentQuestionSchema, AssessmentResponse,
    AssessmentSubmission, AssessmentResultResponse, PersonalizedAssessmentRequest,
    AssessmentHistoryItem, QuestionResultDetail
)
from backend.app.schemas.learning import LearningPlanGenerateRequest, LearningPlanDetailResponse, LearningActivityResponse, RAGQueryRequest, GroundedRAGResponse
from backend.app.schemas.ai_operation import AIOperationResponse, AIUsageSummary
from backend.app.schemas.dashboard import DashboardSummaryResponse

__all__ = [
    "UserCreate", "UserLogin", "UserResponse", "Token",
    "ProfileCreate", "ProfileUpdate", "ProfileResponse",
    "ResumeResponse", "ResumeAnalysisRequest",
    "JobDescriptionCreate", "JobDescriptionResponse", "JobAnalysisRequest",
    "SkillCreate", "SkillResponse", "StudentSkillResponse", "SkillMatrixItem", "SkillGapResponse", "RecommendedActionResponse",
    "CandidateJDSkillItem", "CandidateJDComparisonResponse",
    "EvidenceCreate", "EvidenceResponse",
    "GitHubConnectRequest", "GitHubRepoInfo", "GitHubAnalysisResponse",
    "AssessmentQuestionSchema", "AssessmentResponse", "AssessmentSubmission", "AssessmentResultResponse", "PersonalizedAssessmentRequest",
    "AssessmentHistoryItem", "QuestionResultDetail",
    "LearningPlanGenerateRequest", "LearningPlanDetailResponse", "LearningActivityResponse", "RAGQueryRequest", "GroundedRAGResponse",
    "AIOperationResponse", "AIUsageSummary",
    "DashboardSummaryResponse"
]
