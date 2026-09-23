from fastapi import APIRouter
from backend.app.api.routes import (
    auth, profile, resume, jobs, skills, evidence,
    github, assessments, learning, feedback, dashboard, ai, practice
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(profile.router, prefix="/profile", tags=["Student Profile"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume Processing"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Job Description Processing"])
api_router.include_router(skills.router, prefix="/skills", tags=["Skill Gap Engine"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["Evidence Collection"])
api_router.include_router(github.router, prefix="/github", tags=["GitHub Integration"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Objective Assessments"])
api_router.include_router(practice.router, prefix="/practice", tags=["Skill & Topic Practice Engine"])
api_router.include_router(learning.router, prefix="/learning", tags=["Learning Plan & RAG"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback History"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Gateway & Usage Auditing"])

