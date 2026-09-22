from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.foundry_assessment import AssessmentStartRequest, AssessmentStartResponse
from backend.app.ai.ai_gateway import AIGateway
from backend.app.config.settings import settings

router = APIRouter()


@router.post("/start", response_model=AssessmentStartResponse)
def start_assessment(req: AssessmentStartRequest, db: Session = Depends(get_db)):
    """Direct integration point for Microsoft AI Foundry PlacementPreparationAgent (Version 4).
    Enforces real AI generation with zero predefined questions and zero mock fallbacks.
    """
    if not req.role.strip() or not req.job_description.strip() or not req.resume.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fields 'role', 'job_description', and 'resume' must all be non-empty."
        )

    if not settings.FOUNDRY_PROJECT_ENDPOINT.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "FOUNDRY_PROJECT_ENDPOINT is not configured in .env. "
                "Please configure a valid Azure AI Foundry project endpoint."
            )
        )

    task_prompt = req.task.strip() if req.task and req.task.strip() else (
        "Generate 5 personalized assessment questions based specifically on the candidate's resume, the job description, and the target role.\n\n"
        "Do not generate generic questions.\n\n"
        "For every question, briefly explain why it is relevant to this candidate and role."
    )

    payload = {
        "role": req.role.strip(),
        "job_description": req.job_description.strip(),
        "resume": req.resume.strip(),
        "task": task_prompt
    }

    try:
        result = AIGateway.execute(
            db=db,
            user_id=None,
            operation_type="ASSESSMENT_GENERATION",
            payload=payload,
            response_model=AssessmentStartResponse,
            force_refresh=True
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e).lower()
        if "authentication" in err_msg or "unauthorized" in err_msg or "credential" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Azure authentication failure. Please ensure 'az login' is authenticated."
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Microsoft Foundry execution error: {str(e)}"
        )
