from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AssessmentQuestionSchema(BaseModel):
    id: int
    question: str
    options: List[str]
    skill: str
    difficulty: str
    topic: Optional[str] = "General"
    concept: Optional[str] = "Core Concept"
    why_the_question_is_relevant: Optional[str] = None
    # Note: correct_answer and explanation omitted when serving questions to student


class AssessmentQuestionAdminSchema(AssessmentQuestionSchema):
    correct_answer: str
    explanation: str


class PersonalizedAssessmentRequest(BaseModel):
    role: Optional[str] = Field(default=None, description="Optional target role override; defaults to active target job title")
    job_id: Optional[int] = Field(default=None, description="Target job ID (defaults to active target job)")
    job_description: Optional[str] = Field(default=None, description="Optional JD text (defaults to latest uploaded)")
    resume: Optional[str] = Field(default=None, description="Optional resume text (defaults to latest uploaded)")
    num_questions: int = Field(default=5, ge=1, le=20, description="Number of questions to generate (e.g. 5, 10, 15, 20)")


class AssessmentResponse(BaseModel):
    id: int
    candidate_id: Optional[int] = None
    job_id: Optional[int] = None
    skill_id: Optional[int] = None
    skill_name: Optional[str] = None
    title: str
    role: Optional[str] = None
    difficulty: str
    total_questions: int
    status: str = "pending"
    assessment_mode: str = "full_assessment"
    topic: Optional[str] = None
    canonical_skill_id: Optional[str] = None
    questions: List[AssessmentQuestionSchema]
    created_at: datetime

    class Config:
        from_attributes = True


class AssessmentSubmission(BaseModel):
    assessment_id: int
    answers: Dict[str, str]  # question_id (as str or int key) -> selected option string
    idempotency_key: Optional[str] = None
    duration_seconds: Optional[int] = None


class QuestionResultDetail(BaseModel):
    question_id: int
    question: str
    options: Optional[List[str]] = None
    selected_answer: Optional[str]
    correct_answer: str
    is_correct: bool
    explanation: str
    topic: Optional[str] = None
    concept: Optional[str] = None
    skill: Optional[str] = None
    why_the_question_is_relevant: Optional[str] = None


class AssessmentResultResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    attempt_number: int = 1
    title: Optional[str] = None
    skill_id: Optional[int] = None
    skill_name: Optional[str] = "General"
    role: Optional[str] = None
    score_percentage: float
    assessment_mode: str = "full_assessment"
    topic: Optional[str] = None
    total_questions: int
    correct_count: int
    passed: bool
    analysis_status: str = "pending"  # "pending", "completed", "failed"
    analysis_error: Optional[str] = None
    new_confidence: str
    new_demonstrated_level: str
    per_skill_scores: Optional[Dict[str, float]] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    skill_gaps: List[str] = []
    topics_to_improve: List[str] = []
    priority_areas: List[str] = []
    improvement_plan: List[str] = []
    reassessment_recommendations: Optional[str] = None
    summary_feedback: Optional[str] = None
    details: List[QuestionResultDetail] = []
    completed_at: datetime


class AssessmentHistoryItem(BaseModel):
    attempt_id: int
    assessment_id: int
    attempt_number: int = 1
    title: str = "Assessment"
    role: str
    score_percentage: float
    total_questions: int
    correct_count: int
    passed: bool
    analysis_status: str = "pending"  # "pending", "completed", "failed"
    difficulty: Optional[str] = "Intermediate"
    strengths: List[str] = []
    weaknesses: List[str] = []
    skill_gaps: List[str] = []
    summary_feedback: Optional[str] = None
    improvement_plan: List[str] = []
    completed_at: datetime

    class Config:
        from_attributes = True
