from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


# 1. Resume Analysis Response
class ExtractedSkill(BaseModel):
    name: str
    category: str = "Programming"  # Programming, Framework, Database, Cloud, etc.
    claimed_level: str = "Intermediate"  # Beginner, Intermediate, Advanced


class ExtractedProject(BaseModel):
    name: str
    description: str
    technologies: List[str] = []
    highlights: List[str] = []


class ResumeAnalysisResponse(BaseModel):
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    education: List[str] = []
    experience: List[str] = []
    skills: List[ExtractedSkill] = []
    projects: List[ExtractedProject] = []
    certifications: List[str] = []
    summary: str = ""

    @field_validator("education", "experience", "certifications", mode="before")
    @classmethod
    def normalize_string_list(cls, v):
        if not isinstance(v, list):
            return []
        normalized = []
        for item in v:
            if isinstance(item, dict):
                parts = [str(val).strip() for val in item.values() if val and str(val).strip()]
                normalized.append(" - ".join(parts))
            elif item is not None:
                normalized.append(str(item).strip())
        return normalized


# 2. Job Description Analysis Response
class JobSkillRequirement(BaseModel):
    name: str
    category: str = "Programming"
    importance: str = "Required"  # Required or Preferred
    expected_level: str = "Intermediate"


class JobAnalysisResponse(BaseModel):
    role_title: str
    company_name: Optional[str] = None
    required_skills: List[JobSkillRequirement] = []
    preferred_skills: List[JobSkillRequirement] = []
    assessment_areas: List[str] = []
    key_responsibilities: List[str] = []
    role_expectations: str = ""
    experience_required: str = ""


# 3. Learning Plan Response
class LearningDayActivity(BaseModel):
    day: int = Field(..., ge=1, le=7)
    topic: str
    skill: str
    activity_type: str = "theory"  # theory, practice, quiz, project
    objective: str
    resource_description: str
    resource_url: Optional[str] = None


class LearningPlanResponse(BaseModel):
    target_role: str
    overview: str
    days: List[LearningDayActivity] = []


# 4. Personalized Assessment Question Generation Response
class AssessmentMCQItem(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    skill: str
    difficulty: str = "Intermediate"
    topic: str = "General"
    concept: str = "Core Concept"
    why_the_question_is_relevant: str = "Evaluates required competency for the target role."


class AssessmentGenerationResponse(BaseModel):
    title: str = "Personalized Placement Assessment"
    role: str
    total_questions: int
    questions: List[AssessmentMCQItem] = []
    overview: Optional[str] = None


# 5. Assessment Result Analysis Response (AI-powered post-submission evaluation)
class AssessmentResultAnalysisResponse(BaseModel):
    role: str = "Target Role"
    strengths: List[str] = []
    weaknesses: List[str] = []
    skill_gaps: List[str] = []
    topics_to_improve: List[str] = []
    priority_areas: List[str] = []
    improvement_plan: List[str] = []
    reassessment_recommendations: Optional[str] = None
    summary_feedback: Optional[str] = None



# 7. Grounded RAG Answer Response
class RAGCitation(BaseModel):
    document_id: str
    title: str
    source: str
    snippet: str


class RAGAnswerResponse(BaseModel):
    question: str
    answer: str
    grounded: bool = True
    citations: List[RAGCitation] = []
    confidence: str = "High"
