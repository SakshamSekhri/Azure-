import re
import hashlib
import difflib
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta

from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.evidence import Evidence
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.profile import StudentProfile
from backend.app.ai.ai_gateway import AIGateway
from backend.app.schemas.ai import (
    AssessmentGenerationResponse,
    AssessmentMCQItem,
    AssessmentResultAnalysisResponse
)
from backend.app.schemas.assessment import (
    AssessmentResponse,
    AssessmentQuestionSchema,
    AssessmentResultResponse,
    QuestionResultDetail,
    AssessmentHistoryItem
)
from backend.app.services.placement_profile_service import PlacementProfileService
from backend.app.services.skill_service import SkillService
from backend.app.services.skill_canonicalizer import canonicalize_skill
from backend.app.services.job_service import JobService
from backend.app.core.logging import logger


def _compute_question_hash(question_text: str) -> str:
    """Deterministic hash of stripped alphanumeric question stem for exact duplicate check."""
    normalized = re.sub(r"[^a-z0-9]", "", question_text.lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _validate_question_quality(q: AssessmentMCQItem) -> Tuple[bool, str]:
    """Strict Question Quality Validation (Requirement 9).
    Validates MCQ structure, option count, uniqueness, correct answer matching,
    answer leakage, and placeholder prevention.
    """
    if not q.question or len(q.question.strip()) < 15:
        return False, "Question stem is too short or empty."

    if not q.options or len(q.options) != 4:
        return False, f"Question must have exactly 4 options, found {len(q.options) if q.options else 0}."

    cleaned_options = [opt.strip() for opt in q.options if opt and opt.strip()]
    if len(cleaned_options) != 4:
        return False, "All 4 options must be non-empty strings."

    lower_options = [opt.lower() for opt in cleaned_options]
    if len(set(lower_options)) != 4:
        return False, "All 4 options must be unique and distinct."

    corr = q.correct_answer.strip()
    if not corr:
        return False, "Missing correct_answer."

    matching_opts = [opt for opt in cleaned_options if opt.lower() == corr.lower()]
    if len(matching_opts) != 1:
        return False, f"correct_answer '{corr}' must match exactly one of the 4 options."

    # Prevent placeholder/dummy options (Requirement 9 & 11)
    if set(lower_options) in (
        {"option a", "option b", "option c", "option d"},
        {"a", "b", "c", "d"},
        {"true", "false", "none of the above", "all of the above"}
    ):
        return False, "Malformed options: placeholder labels without technical content."

    # Answer leakage prevention: question stem must not directly give away the correct answer
    stem_lower = q.question.strip().lower()
    corr_lower = corr.lower()
    if f"the answer is {corr_lower}" in stem_lower or f"correct answer is {corr_lower}" in stem_lower:
        return False, f"Answer leakage detected in question stem for '{corr}'."

    # Valid technical skill
    if not q.skill or len(q.skill.strip()) < 2:
        return False, "Question missing valid skill attribution."

    return True, "Valid"


class AssessmentService:
    @staticmethod
    def list_assessments(db: Session, user_id: int) -> List[Assessment]:
        """List active personalized assessments for the candidate with strict ownership (Requirement 12)."""
        return (
            db.query(Assessment)
            .filter(Assessment.candidate_id == user_id)
            .order_by(Assessment.created_at.desc())
            .all()
        )

    @staticmethod
    def get_assessment(db: Session, assessment_id: int, user_id: Optional[int] = None) -> AssessmentResponse:
        """Serve public assessment questions omitting correct answers and explanations.
        Enforces candidate ownership (Requirement 12).
        AssessmentQuestion is the authoritative single source of truth (Requirement 11).
        """
        query = db.query(Assessment).filter(Assessment.id == assessment_id)
        if user_id is not None:
            query = query.filter((Assessment.candidate_id == user_id) | (Assessment.candidate_id.is_(None)))

        assessment = query.first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        # Single source of truth: Load from assessment_questions table
        db_questions = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.id.asc())
            .all()
        )

        public_questions = []
        if db_questions:
            for idx, q in enumerate(db_questions, start=1):
                public_questions.append(AssessmentQuestionSchema(
                    id=q.id,
                    question=q.question,
                    options=q.options if isinstance(q.options, list) else [],
                    skill=q.skill or assessment.role or "General",
                    difficulty=q.difficulty or assessment.difficulty,
                    topic=q.topic or "General",
                    concept=q.concept or "Core Concept",
                    why_the_question_is_relevant=q.why_the_question_is_relevant
                ))
        elif assessment.questions_json:
            # Legacy fallback for pre-migration records only
            for q in assessment.questions_json:
                public_questions.append(AssessmentQuestionSchema(
                    id=q.get("id"),
                    question=q.get("question"),
                    options=q.get("options", []),
                    skill=q.get("skill", assessment.role or "General"),
                    difficulty=q.get("difficulty", assessment.difficulty),
                    topic=q.get("topic", "General"),
                    concept=q.get("concept", "Core Concept"),
                    why_the_question_is_relevant=q.get("why_the_question_is_relevant")
                ))

        skill_name = assessment.skill.name if assessment.skill else (assessment.role or "Personalized")
        return AssessmentResponse(
            id=assessment.id,
            candidate_id=assessment.candidate_id,
            job_id=assessment.job_id,
            skill_id=assessment.skill_id,
            skill_name=skill_name,
            title=assessment.title,
            role=assessment.role,
            difficulty=assessment.difficulty,
            total_questions=len(public_questions),
            status=assessment.status or "pending",
            assessment_mode=getattr(assessment, "assessment_mode", "full_assessment") or "full_assessment",
            topic=getattr(assessment, "topic", None),
            canonical_skill_id=getattr(assessment, "canonical_skill_id", None),
            questions=public_questions,
            created_at=assessment.created_at
        )

    @staticmethod
    def generate_personalized_assessment(
        db: Session,
        user_id: int,
        role: Optional[str] = None,
        job_id: Optional[int] = None,
        resume_text: Optional[str] = None,
        jd_text: Optional[str] = None,
        num_questions: int = 5
    ) -> AssessmentResponse:
        """Dynamically generate personalized assessment questions strictly using Azure AI Foundry.
        ZERO PREDEFINED QUESTIONS. Grounded in normalized PlacementProfile, candidate skill gaps,
        and per-skill adaptive difficulty (Requirements 2, 3, 6, 7, 8, 9, 10).
        """
        # 1. Authoritative Active Target Job resolution (Single Source of Truth)
        active_job = JobService.get_active_target_job(db, user_id, job_id=job_id)

        # Enforce Target Job as single source of truth for the role
        if active_job and active_job.title:
            role = active_job.title
        elif not role:
            role = "Target Role"

        # Fetch unified Placement Profile for this active job (Requirement 3)
        profile_data = PlacementProfileService.get_placement_profile(
            db, user_id, job_id=(active_job.id if active_job else None)
        )

        if not resume_text and profile_data.active_resume_id:
            res_obj = db.query(Resume).filter(Resume.id == profile_data.active_resume_id).first()
            if res_obj and res_obj.raw_text:
                resume_text = res_obj.raw_text

        if not jd_text and active_job and active_job.raw_text:
            jd_text = active_job.raw_text
        elif not jd_text and profile_data.active_jd_id:
            jd_obj = db.query(JobDescription).filter(JobDescription.id == profile_data.active_jd_id).first()
            if jd_obj and jd_obj.raw_text:
                jd_text = jd_obj.raw_text

        has_resume = profile_data.has_resume or bool(resume_text and resume_text.strip())
        has_jd = bool((active_job and active_job.raw_text and active_job.raw_text.strip()) or (jd_text and jd_text.strip()) or profile_data.has_jd)

        if not has_resume or not has_jd:
            missing = []
            if not has_resume:
                missing.append("resume")
            if not has_jd:
                missing.append("target job description")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Please upload your {' and '.join(missing)} before generating a personalized assessment. An active Target Job is required."
            )

        # 2. Skill-Level Adaptive Allocation (Requirements 6 & 7)
        # Prioritize: 1. Required JD skills that are gaps / weak (<50%)
        #             2. High-impact missing skills
        #             3. Previously weak topics
        #             4. Previously tested skills to measure progress
        skill_allocation: List[Dict[str, Any]] = []

        gaps = profile_data.skill_gaps
        reqs = profile_data.required_skills
        scores = profile_data.skill_scores

        allocated_count = 0
        allocated_skills: Set[str] = set()

        # Prioritize weak skills and critical gaps first
        for gap in gaps:
            if allocated_count >= num_questions:
                break
            prev_s = scores.get(gap.canonical_id)
            diff = "Beginner" if prev_s is not None and prev_s < 50.0 else "Intermediate"
            skill_allocation.append({
                "skill": gap.display_name,
                "canonical_id": gap.canonical_id,
                "difficulty": diff,
                "reason": "Critical skill gap vs JD requirement"
            })
            allocated_skills.add(gap.canonical_id)
            allocated_count += 1

        # Fill remaining slots with other required JD skills
        for req in reqs:
            if allocated_count >= num_questions:
                break
            if req.canonical_id in allocated_skills:
                continue
            prev_s = scores.get(req.canonical_id)
            if prev_s is not None and prev_s >= 80.0:
                diff = "Advanced"
            elif prev_s is not None and prev_s < 60.0:
                diff = "Beginner"
            else:
                diff = "Intermediate"

            skill_allocation.append({
                "skill": req.display_name,
                "canonical_id": req.canonical_id,
                "difficulty": diff,
                "reason": "Required JD technical competency"
            })
            allocated_skills.add(req.canonical_id)
            allocated_count += 1

        # If still slots remaining, distribute across claimed skills
        for cl in profile_data.claimed_skills:
            if allocated_count >= num_questions:
                break
            if cl.canonical_id in allocated_skills:
                continue
            skill_allocation.append({
                "skill": cl.display_name,
                "canonical_id": cl.canonical_id,
                "difficulty": "Intermediate",
                "reason": "Verification of resume claimed skill"
            })
            allocated_skills.add(cl.canonical_id)
            allocated_count += 1

        # Fallback if no specific skills extracted yet
        if not skill_allocation:
            skill_allocation = [
                {"skill": role, "canonical_id": "general", "difficulty": "Intermediate", "reason": "Target role core competency"}
                for _ in range(num_questions)
            ]

        # Overall representative difficulty
        avg_score = profile_data.assessment_history[0]["score_percentage"] if profile_data.assessment_history else None
        overall_difficulty = "Advanced" if avg_score and avg_score >= 80.0 else ("Beginner" if avg_score and avg_score < 60.0 else "Intermediate")

        # 3. Question & Concept Repetition Prevention (Requirement 10)
        past_questions_query = (
            db.query(AssessmentQuestion.question, AssessmentQuestion.concept, AssessmentQuestion.question_hash)
            .join(Assessment, AssessmentQuestion.assessment_id == Assessment.id)
            .filter(Assessment.candidate_id == user_id)
            .order_by(AssessmentQuestion.id.desc())
            .limit(50)
            .all()
        )
        excluded_questions = [row[0] for row in past_questions_query if row[0]]
        excluded_concepts = list({row[1] for row in past_questions_query if row[1] and row[1].lower() != "core concept"})
        past_hashes = {row[2] for row in past_questions_query if row[2]}

        # 4. Construct Compact Context (Requirement 17)
        compact_ctx = PlacementProfileService.build_compact_ai_context(profile_data, num_questions, target_role=role)

        payload = {
            "role": role,
            "resume": (resume_text or "").strip() or compact_ctx,
            "job_description": (jd_text or "").strip() or compact_ctx,
            "num_questions": num_questions,
            "difficulty": overall_difficulty,
            "skill_allocation": skill_allocation,
            "candidate_skills": [s.display_name for s in profile_data.claimed_skills],
            "candidate_projects": [p.get("name") for p in profile_data.projects if p.get("name")],
            "candidate_experience": profile_data.experience[:3],
            "candidate_education": profile_data.education[:2],
            "candidate_certifications": profile_data.certifications[:3],
            "required_skills": [r.display_name for r in profile_data.required_skills],
            "preferred_skills": [p.display_name for p in profile_data.preferred_skills],
            "identified_gaps": [g.display_name for g in profile_data.skill_gaps],
            "previous_score": avg_score,
            "weak_topics": profile_data.weak_topics[:6],
            "previous_performance": profile_data.assessment_history[:3],
            "excluded_questions": excluded_questions[:15],
            "excluded_concepts": excluded_concepts[:20]
        }

        # 5. Dynamic Generation via AIGateway with Quality Validation and 1 Retry (Requirement 9)
        max_attempts = 2
        filtered_questions: List[AssessmentMCQItem] = []

        for gen_attempt in range(1, max_attempts + 1):
            try:
                ai_response: AssessmentGenerationResponse = AIGateway.execute(
                    db=db,
                    user_id=user_id,
                    operation_type="ASSESSMENT_QUESTION_GENERATION",
                    payload=payload,
                    response_model=AssessmentGenerationResponse,
                    force_refresh=True
                )
            except Exception as e:
                logger.error(f"Foundry generation failed on attempt {gen_attempt}: {e}")
                if gen_attempt >= max_attempts:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Unable to generate personalized assessment questions right now. Please try again."
                    )
                continue

            raw_questions = ai_response.questions or []
            if not raw_questions:
                if gen_attempt < max_attempts:
                    logger.warning("Foundry returned 0 questions. Retrying generation...")
                    continue
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unable to generate personalized assessment questions right now. Please try again."
                )

            # Strict quality and deduplication filter
            seen_stems: Set[str] = set()
            seen_concepts: Set[str] = set()
            candidate_valid_questions = []

            for q in raw_questions:
                # 5a. Quality check
                is_valid, reason = _validate_question_quality(q)
                if not is_valid:
                    logger.warning(f"Discarding malformed question: {reason}")
                    continue

                q_text = q.question.strip()
                q_stem_lower = q_text.lower()
                q_hash = _compute_question_hash(q_text)
                q_concept = (q.concept or "Core Concept").strip()
                q_concept_lower = q_concept.lower()

                # 5b. Exact duplicate check
                if q_hash in past_hashes or q_stem_lower in seen_stems:
                    logger.warning(f"Discarding exact duplicate question hash: {q_hash[:10]}")
                    continue

                # 5c. Intra-batch concept check
                if q_concept_lower != "core concept" and q_concept_lower in seen_concepts:
                    logger.warning(f"Discarding intra-batch duplicate concept: {q_concept}")
                    continue

                # 5d. Near-duplicate similarity check
                is_near_dup = False
                for past_q in excluded_questions:
                    sim = difflib.SequenceMatcher(None, q_stem_lower, past_q.lower()).ratio()
                    if sim > 0.80:
                        is_near_dup = True
                        logger.warning(f"Discarding near-duplicate question ({sim:.2f}): {q_text[:40]}")
                        break

                if not is_near_dup:
                    seen_stems.add(q_stem_lower)
                    if q_concept_lower != "core concept":
                        seen_concepts.add(q_concept_lower)
                    candidate_valid_questions.append(q)

            if len(candidate_valid_questions) >= num_questions:
                filtered_questions = candidate_valid_questions
                break
            elif gen_attempt < max_attempts:
                logger.warning(
                    f"Only {len(candidate_valid_questions)} valid questions generated. "
                    f"Initiating corrective regeneration attempt {gen_attempt + 1}..."
                )
            else:
                filtered_questions = candidate_valid_questions

        if not filtered_questions:
            # ZERO predefined questions, zero fallback questions (Requirement 2 & 9)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Assessment generation quality check failed. Please try again."
            )

        questions_list = [q.model_dump() for q in filtered_questions]

        # 6. Store Assessment in Database
        assessment = Assessment(
            candidate_id=user_id,
            job_id=profile_data.active_jd_id,
            skill_id=None,
            title=ai_response.title or f"Personalized Assessment for {role}",
            role=role,
            difficulty=overall_difficulty,
            question_count=len(questions_list),
            status="pending",
            questions_json=questions_list,  # Retained for legacy compatibility
            metadata_json={
                "overview": ai_response.overview,
                "total_generated": len(questions_list),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "identified_gaps": [g.display_name for g in profile_data.skill_gaps]
            }
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # 7. Store Authoritative Questions in assessment_questions Table (Requirement 11)
        for idx, q_dict in enumerate(questions_list, start=1):
            raw_skill = q_dict.get("skill") or role
            canon_skill = canonicalize_skill(raw_skill)
            q_hash = _compute_question_hash(q_dict.get("question", ""))

            q_record = AssessmentQuestion(
                assessment_id=assessment.id,
                question=q_dict.get("question"),
                options=q_dict.get("options", []),
                correct_answer=q_dict.get("correct_answer", ""),
                explanation=q_dict.get("explanation", ""),
                canonical_skill_id=canon_skill.canonical_id,
                skill=canon_skill.display_name,
                topic=q_dict.get("topic", "General"),
                concept=q_dict.get("concept", "Core Concept"),
                difficulty=q_dict.get("difficulty", overall_difficulty),
                why_the_question_is_relevant=q_dict.get("why_the_question_is_relevant"),
                question_hash=q_hash
            )
            db.add(q_record)
        db.commit()

        return AssessmentService.get_assessment(db, assessment.id, user_id=user_id)

    @staticmethod
    def submit_assessment(
        db: Session,
        user_id: int,
        assessment_id: int,
        submitted_answers: Dict[str, str],
        duration_seconds: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        background_tasks: Any = None
    ) -> AssessmentResultResponse:
        """Deterministically score assessment, persist every answer, calibrate per-skill evidence,
        and trigger AI Result Analysis asynchronously.
        Strictly enforces candidate ownership (Requirement 12).
        Explicit multi-attempt tracking (Requirement 23 & 24).
        Fast submission: commit before background AI analysis.
        """
        # 1. Candidate Ownership Verification
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                (Assessment.candidate_id == user_id) | (Assessment.candidate_id.is_(None))
            )
            .first()
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        # 2. Prevent Duplicate Submissions (Requirement 10)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=15)
        existing_recent = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.completed_at >= recent_cutoff
            )
            .order_by(AssessmentAttempt.completed_at.desc())
            .first()
        )
        if existing_recent:
            existing_idemp = (existing_recent.result_summary_json or {}).get("idempotency_key") if existing_recent.result_summary_json else None
            if (idempotency_key and existing_idemp == idempotency_key) or (existing_recent.answers_json == submitted_answers):
                logger.info(f"Duplicate submission detected for user {user_id}, assessment {assessment_id}. Returning existing attempt {existing_recent.id}.")
                return AssessmentService.build_result_response_from_attempt(existing_recent, assessment, db=db)

        # 3. Authoritative Questions from assessment_questions table (Requirement 11)
        db_questions = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.id.asc())
            .all()
        )

        questions_to_score = []
        if db_questions:
            for q in db_questions:
                questions_to_score.append({
                    "id": q.id,
                    "question": q.question,
                    "options": q.options if isinstance(q.options, list) else [],
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "canonical_skill_id": q.canonical_skill_id or canonicalize_skill(q.skill or assessment.role or "General").canonical_id,
                    "skill": q.skill or assessment.role or "General",
                    "topic": q.topic or "General",
                    "concept": q.concept or "Core Concept",
                    "difficulty": q.difficulty or assessment.difficulty,
                    "why_the_question_is_relevant": q.why_the_question_is_relevant,
                    "_db_obj": q
                })
        elif assessment.questions_json:
            for q in assessment.questions_json:
                questions_to_score.append({
                    "id": q.get("id"),
                    "question": q.get("question"),
                    "options": q.get("options", []),
                    "correct_answer": q.get("correct_answer", ""),
                    "explanation": q.get("explanation", ""),
                    "canonical_skill_id": canonicalize_skill(q.get("skill") or assessment.role or "General").canonical_id,
                    "skill": q.get("skill", assessment.role or "General"),
                    "topic": q.get("topic", "General"),
                    "concept": q.get("concept", "Core Concept"),
                    "difficulty": q.get("difficulty", assessment.difficulty),
                    "why_the_question_is_relevant": q.get("why_the_question_is_relevant"),
                    "_db_obj": None
                })

        total_questions = len(questions_to_score)
        if total_questions == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment contains no questions.")

        # 4. Deterministic Scoring & Per-Skill Tracking (Requirements 6 & 17)
        correct_count = 0
        details: List[QuestionResultDetail] = []
        strengths: List[str] = []
        weaknesses: List[str] = []
        topics_to_improve: List[str] = []
        per_skill_stats: Dict[str, Dict[str, int]] = {}

        for q in questions_to_score:
            q_id_str = str(q["id"])
            correct_ans = str(q["correct_answer"]).strip()
            user_ans = str(submitted_answers.get(q_id_str, "")).strip()

            is_correct = (user_ans.lower() == correct_ans.lower() and user_ans != "")
            s_name = (q.get("skill") or assessment.role or "General").strip()

            if s_name not in per_skill_stats:
                per_skill_stats[s_name] = {"total": 0, "correct": 0}
            per_skill_stats[s_name]["total"] += 1

            if is_correct:
                correct_count += 1
                per_skill_stats[s_name]["correct"] += 1
                if s_name not in strengths:
                    strengths.append(s_name)
            else:
                if s_name not in weaknesses:
                    weaknesses.append(s_name)
                if q["topic"] not in topics_to_improve:
                    topics_to_improve.append(q["topic"])

            details.append(QuestionResultDetail(
                question_id=q["id"],
                question=q["question"],
                options=q.get("options", []),
                selected_answer=user_ans if user_ans else "Unanswered",
                correct_answer=correct_ans,
                is_correct=is_correct,
                explanation=q["explanation"],
                topic=q["topic"],
                concept=q.get("concept"),
                skill=s_name,
                why_the_question_is_relevant=q["why_the_question_is_relevant"]
            ))

        score_percentage = round((correct_count / total_questions) * 100.0, 1)

        # 5. Calibrate Per-Skill Performance in StudentSkill Records (Requirements 4, 5, 6)
        per_skill_scores: Dict[str, float] = {}
        for s_name, stats in per_skill_stats.items():
            skill_score = round((stats["correct"] / max(stats["total"], 1)) * 100.0, 1)
            per_skill_scores[s_name] = skill_score

            # Canonicalize skill
            skill = SkillService.get_or_create_skill(db, s_name)

            # Insert or update StudentSkill
            student_skill = db.query(StudentSkill).filter(
                StudentSkill.user_id == user_id,
                StudentSkill.skill_id == skill.id
            ).first()

            if not student_skill:
                student_skill = StudentSkill(
                    user_id=user_id,
                    skill_id=skill.id,
                    confidence="Low",
                    evidence_count=0,
                    is_claimed=0,
                    is_required_by_jd=0
                )
                db.add(student_skill)
                db.flush()

            # Multi-source evidence checks (Requirement 5)
            has_github = db.query(Evidence).filter(
                Evidence.user_id == user_id,
                Evidence.skill_id == skill.id,
                Evidence.type == "GitHub"
            ).count() > 0
            claimed = bool(student_skill.is_claimed)
            total_questions_tested = stats["total"]

            # Guard against single-question inflation (Requirement 5)
            if skill_score >= 80.0:
                s_dem = "Advanced" if (total_questions_tested >= 2 or (has_github and claimed)) else "Intermediate"
            elif skill_score >= 60.0:
                s_dem = "Intermediate"
            else:
                s_dem = "Beginner"

            if skill_score >= 75.0:
                s_conf = "High" if (total_questions_tested >= 2 or (has_github and claimed)) else "Medium"
            elif skill_score >= 50.0:
                s_conf = "Medium"
            else:
                s_conf = "Low"

            student_skill.assessment_score = skill_score
            student_skill.demonstrated_level = s_dem
            student_skill.confidence = s_conf
            student_skill.last_updated = datetime.now(timezone.utc)

        # 6. Explicit Attempt Tracking (Requirements 23 & 24)
        prev_attempts_count = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.assessment_id == assessment.id,
            AssessmentAttempt.user_id == user_id
        ).count()
        attempt_number = prev_attempts_count + 1

        # Initial deterministic result summary
        result_summary = {
            "analysis_status": "pending",
            "analysis_error": None,
            "idempotency_key": idempotency_key,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "skill_gaps": list(set(weaknesses)),
            "topics_to_improve": topics_to_improve,
            "priority_areas": list(set(weaknesses)),
            "improvement_plan": [],
            "reassessment_recommendations": None,
            "summary_feedback": None,
            "per_skill_scores": per_skill_scores,
            "details": [d.model_dump() for d in details]
        }

        attempt = AssessmentAttempt(
            user_id=user_id,
            assessment_id=assessment.id,
            attempt_number=attempt_number,
            duration_seconds=duration_seconds,
            analysis_status="pending",
            score_percentage=score_percentage,
            total_questions=total_questions,
            correct_count=correct_count,
            answers_json=submitted_answers,
            result_summary_json=result_summary,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(attempt)
        db.flush()

        # 7. Persist every answer to assessment_answers with attempt_id
        for q in questions_to_score:
            if q.get("_db_obj"):
                q_id_str = str(q["id"])
                user_ans = str(submitted_answers.get(q_id_str, "")).strip()
                correct_ans = str(q["correct_answer"]).strip()
                is_correct = (user_ans.lower() == correct_ans.lower() and user_ans != "")
                ans_record = AssessmentAnswer(
                    assessment_id=assessment.id,
                    attempt_id=attempt.id,
                    question_id=q["_db_obj"].id,
                    candidate_id=user_id,
                    selected_answer=user_ans if user_ans else "Unanswered",
                    correct_answer=correct_ans,
                    is_correct=is_correct,
                    time_taken=duration_seconds,
                    answered_at=datetime.now(timezone.utc)
                )
                db.add(ans_record)

        assessment.status = "completed"
        db.commit()
        db.refresh(attempt)

        # 8. Asynchronous AI Diagnostic Analysis enqueuing (Requirement 2 & 3)
        if background_tasks is not None:
            background_tasks.add_task(
                AssessmentService.run_background_result_analysis,
                attempt.id,
                user_id,
                assessment.id,
                db=db
            )

        return AssessmentService.build_result_response_from_attempt(attempt, assessment, db=db)

    @staticmethod
    def run_background_result_analysis(
        attempt_id: int,
        user_id: int,
        assessment_id: int,
        db: Optional[Session] = None
    ) -> None:
        """Isolated background worker method to execute AI diagnostic analysis safely."""
        if db is not None:
            try:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
                AssessmentService._execute_ai_analysis_for_attempt(db, attempt_id, user_id, assessment_id)
                return
            except Exception as e:
                logger.debug(f"Direct session unavailable for background task: {e}")

        from backend.app.core.database import SessionLocal
        bg_db = SessionLocal()
        try:
            AssessmentService._execute_ai_analysis_for_attempt(bg_db, attempt_id, user_id, assessment_id)
        except Exception as e:
            logger.error(f"Error in background AI analysis task: {e}")
        finally:
            bg_db.close()

    @staticmethod
    def _execute_ai_analysis_for_attempt(
        db: Session,
        attempt_id: int,
        user_id: int,
        assessment_id: int
    ) -> Optional[AssessmentAttempt]:
        """Execute AI diagnostic analysis for an attempt and update result_summary_json."""
        attempt = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.id == attempt_id,
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.assessment_id == assessment_id
            )
            .first()
        )
        if not attempt:
            logger.warning(f"AssessmentAttempt {attempt_id} not found for background analysis.")
            return None

        # If already completed, nothing to do
        if attempt.analysis_status == "completed":
            return attempt

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        res_sum = dict(attempt.result_summary_json or {})

        # Load questions
        db_questions = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.id.asc())
            .all()
        )
        questions_for_ai = []
        if db_questions:
            for q in db_questions:
                questions_for_ai.append({
                    "id": q.id,
                    "question": q.question,
                    "options": q.options if isinstance(q.options, list) else [],
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "skill": q.skill or (assessment.role if assessment else "General"),
                    "topic": q.topic or "General",
                    "concept": q.concept or "Core Concept",
                    "difficulty": q.difficulty,
                    "why_the_question_is_relevant": q.why_the_question_is_relevant
                })
        else:
            for d in res_sum.get("details", []):
                questions_for_ai.append({
                    "id": d.get("question_id"),
                    "question": d.get("question"),
                    "options": d.get("options", []),
                    "correct_answer": d.get("correct_answer"),
                    "explanation": d.get("explanation"),
                    "skill": d.get("skill"),
                    "topic": d.get("topic"),
                    "concept": d.get("concept"),
                    "why_the_question_is_relevant": d.get("why_the_question_is_relevant")
                })

        profile_data = PlacementProfileService.get_placement_profile(db, user_id)
        role_name = (assessment.role if assessment and assessment.role else None) or "Target Role"

        ai_payload = {
            "role": role_name,
            "score_percentage": attempt.score_percentage,
            "correct_count": attempt.correct_count,
            "total_questions": attempt.total_questions,
            "per_skill_scores": res_sum.get("per_skill_scores", {}),
            "candidate_skills": [s.display_name for s in profile_data.claimed_skills],
            "required_skills": [r.display_name for r in profile_data.required_skills],
            "questions": questions_for_ai,
            "answers": attempt.answers_json
        }

        try:
            ai_analysis: AssessmentResultAnalysisResponse = AIGateway.execute(
                db=db,
                user_id=user_id,
                operation_type="ASSESSMENT_RESULT_ANALYSIS",
                payload=ai_payload,
                response_model=AssessmentResultAnalysisResponse,
                force_refresh=True
            )

            # Safely enrich existing summary without losing deterministic baseline
            if ai_analysis.strengths:
                res_sum["strengths"] = ai_analysis.strengths
            if ai_analysis.weaknesses:
                res_sum["weaknesses"] = ai_analysis.weaknesses
            if ai_analysis.skill_gaps:
                res_sum["skill_gaps"] = ai_analysis.skill_gaps
            if ai_analysis.topics_to_improve:
                res_sum["topics_to_improve"] = ai_analysis.topics_to_improve
            if ai_analysis.priority_areas:
                res_sum["priority_areas"] = ai_analysis.priority_areas
            if ai_analysis.improvement_plan:
                res_sum["improvement_plan"] = ai_analysis.improvement_plan
            if ai_analysis.reassessment_recommendations:
                res_sum["reassessment_recommendations"] = ai_analysis.reassessment_recommendations
            if ai_analysis.summary_feedback:
                res_sum["summary_feedback"] = ai_analysis.summary_feedback

            res_sum["analysis_status"] = "completed"
            res_sum["analysis_error"] = None
            attempt.analysis_status = "completed"
            attempt.result_summary_json = res_sum
            db.commit()
            db.refresh(attempt)
            logger.info(f"AI result analysis completed successfully for attempt {attempt_id}.")
            return attempt
        except Exception as e:
            logger.error(f"AI result analysis failed for attempt {attempt_id}: {e}")
            res_sum["analysis_status"] = "failed"
            res_sum["analysis_error"] = str(e)
            attempt.analysis_status = "failed"
            attempt.result_summary_json = res_sum
            db.commit()
            db.refresh(attempt)
            return attempt

    @staticmethod
    def build_result_response_from_attempt(
        attempt: AssessmentAttempt,
        assessment: Optional[Assessment] = None,
        db: Optional[Session] = None
    ) -> AssessmentResultResponse:
        """Construct full AssessmentResultResponse strictly from stored attempt data and questions.
        Guarantees deterministic display and question-by-question review without AI.
        """
        res_sum = attempt.result_summary_json or {}
        raw_details = res_sum.get("details", [])
        details: List[QuestionResultDetail] = []

        if raw_details:
            for d in raw_details:
                detail_dict = dict(d)
                details.append(QuestionResultDetail.model_validate(detail_dict))
        elif db:
            db_questions = (
                db.query(AssessmentQuestion)
                .filter(AssessmentQuestion.assessment_id == attempt.assessment_id)
                .order_by(AssessmentQuestion.id.asc())
                .all()
            )
            answers_map = attempt.answers_json or {}
            for q in db_questions:
                user_ans = answers_map.get(str(q.id)) or ""
                is_corr = (str(user_ans).strip().lower() == str(q.correct_answer).strip().lower() and user_ans != "")
                details.append(QuestionResultDetail(
                    question_id=q.id,
                    question=q.question,
                    options=q.options if isinstance(q.options, list) else [],
                    selected_answer=user_ans if user_ans else "Unanswered",
                    correct_answer=q.correct_answer,
                    is_correct=is_corr,
                    explanation=q.explanation,
                    topic=q.topic,
                    concept=q.concept,
                    skill=q.skill,
                    why_the_question_is_relevant=q.why_the_question_is_relevant
                ))

        score_pct = attempt.score_percentage
        passed = score_pct >= 60.0
        demonstrated = "Advanced" if score_pct >= 80.0 else ("Intermediate" if score_pct >= 60.0 else "Beginner")
        confidence = "High" if score_pct >= 75.0 else ("Medium" if score_pct >= 50.0 else "Low")
        per_skill_scores = res_sum.get("per_skill_scores", {})
        analysis_status = getattr(attempt, "analysis_status", None) or res_sum.get("analysis_status", "pending")
        analysis_error = res_sum.get("analysis_error")

        role_name = (assessment.role if assessment and assessment.role else None) or "Target Role"
        title_name = (assessment.title if assessment and assessment.title else None) or f"{role_name} Assessment"
        skill_name = (assessment.skill.name if assessment and assessment.skill else None) or role_name

        return AssessmentResultResponse(
            attempt_id=attempt.id,
            assessment_id=attempt.assessment_id,
            attempt_number=attempt.attempt_number or 1,
            title=title_name,
            skill_id=assessment.skill_id if assessment else None,
            skill_name=skill_name,
            role=role_name,
            score_percentage=attempt.score_percentage,
            assessment_mode=(getattr(assessment, "assessment_mode", "full_assessment") if assessment else "full_assessment") or "full_assessment",
            topic=(getattr(assessment, "topic", None) if assessment else None),
            total_questions=attempt.total_questions,
            correct_count=attempt.correct_count,
            passed=passed,
            analysis_status=analysis_status,
            analysis_error=analysis_error,
            new_confidence=confidence,
            new_demonstrated_level=demonstrated,
            per_skill_scores=per_skill_scores,
            strengths=res_sum.get("strengths", []),
            weaknesses=res_sum.get("weaknesses", []),
            skill_gaps=res_sum.get("skill_gaps", []),
            topics_to_improve=res_sum.get("topics_to_improve", []),
            priority_areas=res_sum.get("priority_areas", []),
            improvement_plan=res_sum.get("improvement_plan", []),
            reassessment_recommendations=res_sum.get("reassessment_recommendations"),
            summary_feedback=res_sum.get("summary_feedback"),
            details=details,
            completed_at=attempt.completed_at
        )

    @staticmethod
    def get_assessment_attempt_result(
        db: Session,
        user_id: int,
        assessment_id: int,
        attempt_id: int
    ) -> AssessmentResultResponse:
        """Fetch specific assessment attempt result with strict candidate ownership verification (Requirement 6)."""
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                (Assessment.candidate_id == user_id) | (Assessment.candidate_id.is_(None))
            )
            .first()
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        attempt = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.id == attempt_id,
                AssessmentAttempt.assessment_id == assessment_id
            )
            .first()
        )
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment attempt not found."
            )
        if attempt.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this assessment attempt."
            )

        return AssessmentService.build_result_response_from_attempt(attempt, assessment, db=db)

    @staticmethod
    def get_assessment_result(db: Session, user_id: int, assessment_id: int) -> AssessmentResultResponse:
        """Fetch latest saved assessment attempt result with strict candidate ownership (Requirement 12 & 30)."""
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                (Assessment.candidate_id == user_id) | (Assessment.candidate_id.is_(None))
            )
            .first()
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        attempt = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.user_id == user_id
            )
            .order_by(AssessmentAttempt.attempt_number.desc(), AssessmentAttempt.completed_at.desc())
            .first()
        )
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No completed assessment attempt found for this ID."
            )

        return AssessmentService.build_result_response_from_attempt(attempt, assessment, db=db)

    @staticmethod
    def get_assessment_history(db: Session, user_id: int) -> List[AssessmentHistoryItem]:
        """Fetch complete candidate assessment attempt history with ownership verification (Requirements 12 & 23)."""
        attempts = (
            db.query(AssessmentAttempt)
            .filter(AssessmentAttempt.user_id == user_id)
            .order_by(AssessmentAttempt.completed_at.desc())
            .all()
        )

        history = []
        for att in attempts:
            assessment = db.query(Assessment).filter(Assessment.id == att.assessment_id).first()
            role = assessment.role if assessment and assessment.role else "General Assessment"
            title = assessment.title if assessment and assessment.title else f"{role} Assessment"
            difficulty = assessment.difficulty if assessment else "Intermediate"
            res_sum = att.result_summary_json or {}
            analysis_status = getattr(att, "analysis_status", None) or res_sum.get("analysis_status", "pending")

            history.append(AssessmentHistoryItem(
                attempt_id=att.id,
                assessment_id=att.assessment_id,
                attempt_number=att.attempt_number or 1,
                title=title,
                role=role,
                difficulty=difficulty,
                score_percentage=att.score_percentage,
                total_questions=att.total_questions,
                correct_count=att.correct_count,
                passed=att.score_percentage >= 60.0,
                analysis_status=analysis_status,
                strengths=res_sum.get("strengths", []),
                weaknesses=res_sum.get("weaknesses", []),
                skill_gaps=res_sum.get("skill_gaps", []),
                summary_feedback=res_sum.get("summary_feedback"),
                improvement_plan=res_sum.get("improvement_plan", []),
                completed_at=att.completed_at
            ))
        return history

    @staticmethod
    def retry_assessment_analysis(
        db: Session,
        user_id: int,
        assessment_id: int,
        attempt_id: int,
        background_tasks: Any = None
    ) -> AssessmentResultResponse:
        """Retry failed AI diagnostic analysis for an attempt (Requirement 2)."""
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                (Assessment.candidate_id == user_id) | (Assessment.candidate_id.is_(None))
            )
            .first()
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        attempt = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.id == attempt_id,
                AssessmentAttempt.assessment_id == assessment_id
            )
            .first()
        )
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found.")
        if attempt.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to modify this attempt.")

        attempt.analysis_status = "pending"
        res_sum = dict(attempt.result_summary_json or {})
        res_sum["analysis_status"] = "pending"
        res_sum["analysis_error"] = None
        attempt.result_summary_json = res_sum
        db.commit()
        db.refresh(attempt)

        if background_tasks is not None:
            background_tasks.add_task(AssessmentService.run_background_result_analysis, attempt.id, user_id, assessment_id, db=db)
        else:
            AssessmentService.run_background_result_analysis(attempt.id, user_id, assessment_id, db=db)

        return AssessmentService.build_result_response_from_attempt(attempt, assessment, db=db)

    @staticmethod
    def generate_practice_session(
        db: Session,
        user_id: int,
        skill: str,
        topic: Optional[str] = None,
        num_questions: int = 5,
        difficulty: Optional[str] = None
    ) -> AssessmentResponse:
        """Generate focused dynamic practice MCQs for ANY skill or topic strictly using Azure AI Foundry.
        Zero static questions, zero fallbacks. Adaptive difficulty based on skill/topic history.
        """
        from backend.app.services.skill_topic_service import SkillTopicService

        canon = canonicalize_skill(skill)
        skill_name = canon.display_name
        canonical_id = canon.canonical_id

        # 1. Determine adaptive difficulty if not explicitly overridden
        if not difficulty or difficulty.strip().capitalize() not in ("Beginner", "Intermediate", "Advanced"):
            diff = SkillTopicService.compute_adaptive_difficulty(db, user_id, canonical_id, topic)
        else:
            diff = difficulty.strip().capitalize()

        # 2. Get active target job role or fallback
        active_jd = JobService.get_active_target_job(db, user_id)
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        target_role = (active_jd.title if active_jd and active_jd.title else None) or (profile.target_role if profile and profile.target_role else None) or "Candidate"

        # 3. Question repetition prevention for this candidate & skill
        past_q_query = (
            db.query(AssessmentQuestion.question, AssessmentQuestion.concept, AssessmentQuestion.question_hash)
            .join(Assessment, AssessmentQuestion.assessment_id == Assessment.id)
            .filter(
                Assessment.candidate_id == user_id,
                (AssessmentQuestion.canonical_skill_id == canonical_id) | (AssessmentQuestion.skill.ilike(skill_name))
            )
            .order_by(AssessmentQuestion.id.desc())
            .limit(30)
            .all()
        )
        excluded_questions = [row[0] for row in past_q_query if row[0]]
        excluded_concepts = list({row[1] for row in past_q_query if row[1] and row[1].lower() != "core concept"})
        past_hashes = {row[2] for row in past_q_query if row[2]}

        # 4. Construct AI Foundry Prompt Payload strictly focused on this skill & topic
        topic_str = topic.strip() if (topic and topic.strip()) else f"{skill_name} Core Concepts"
        allocation = [{
            "skill": skill_name,
            "canonical_id": canonical_id,
            "difficulty": diff,
            "topic": topic_str,
            "reason": f"Focused practice session on {topic_str}" if topic else f"Practice on {skill_name}"
        }]

        payload = {
            "role": target_role,
            "target_skill": skill_name,
            "target_topic": topic_str,
            "num_questions": num_questions,
            "difficulty": diff,
            "skill_allocation": allocation,
            "excluded_questions": excluded_questions[:15],
            "excluded_concepts": excluded_concepts[:15],
            "practice_mode": True
        }

        # 5. Dynamic generation via AIGateway with quality validation & 1 retry
        max_attempts = 2
        filtered_questions = []

        for gen_attempt in range(1, max_attempts + 1):
            try:
                ai_response: AssessmentGenerationResponse = AIGateway.execute(
                    db=db,
                    user_id=user_id,
                    operation_type="ASSESSMENT_QUESTION_GENERATION",
                    payload=payload,
                    response_model=AssessmentGenerationResponse,
                    force_refresh=True
                )
            except Exception as e:
                logger.error(f"Foundry practice generation failed attempt {gen_attempt}: {e}")
                if gen_attempt >= max_attempts:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Unable to generate practice questions right now. Please try again."
                    )
                continue

            raw_questions = ai_response.questions or []
            if not raw_questions:
                if gen_attempt < max_attempts:
                    continue
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unable to generate practice questions right now. Please try again."
                )

            seen_stems: Set[str] = set()
            seen_concepts: Set[str] = set()
            batch_valid = []

            for q in raw_questions:
                # Quality check
                is_valid, reason = _validate_question_quality(q)
                if not is_valid:
                    continue

                q_text = q.question.strip()
                q_stem = q_text.lower()
                q_hash = _compute_question_hash(q_text)
                q_concept = (q.concept or "Core Concept").strip()

                if q_hash in past_hashes or q_stem in seen_stems:
                    continue

                is_near_dup = False
                for past_q in excluded_questions:
                    if difflib.SequenceMatcher(None, q_stem, past_q.strip().lower()).ratio() > 0.80:
                        is_near_dup = True
                        break

                if not is_near_dup:
                    seen_stems.add(q_stem)
                    if q_concept.lower() != "core concept":
                        seen_concepts.add(q_concept.lower())
                    batch_valid.append(q)

            if len(batch_valid) >= num_questions:
                filtered_questions = batch_valid[:num_questions]
                break
            elif gen_attempt < max_attempts:
                continue
            else:
                filtered_questions = batch_valid

        if not filtered_questions:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Practice question quality validation check failed. Please retry."
            )

        questions_list = [q.model_dump() for q in filtered_questions]

        # 6. Ensure Skill row exists in DB
        skill_record = SkillService.get_or_create_skill(db, skill_name, canon.category)

        # 7. Persist Assessment record with assessment_mode="practice"
        title_str = f"Practice: {skill_name} — {topic_str}" if topic else f"Practice: {skill_name}"
        assessment = Assessment(
            candidate_id=user_id,
            job_id=None,
            skill_id=skill_record.id,
            canonical_skill_id=canonical_id,
            title=title_str,
            role=skill_name,
            difficulty=diff,
            question_count=len(questions_list),
            status="pending",
            assessment_mode="practice",
            topic=topic_str if topic else None,
            questions_json=questions_list,
            metadata_json={
                "is_practice": True,
                "skill": skill_name,
                "canonical_id": canonical_id,
                "topic": topic_str,
                "overview": ai_response.overview,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # 8. Persist authoritative AssessmentQuestion records
        for q_dict in questions_list:
            q_hash = _compute_question_hash(q_dict.get("question", ""))
            q_record = AssessmentQuestion(
                assessment_id=assessment.id,
                question=q_dict.get("question"),
                options=q_dict.get("options", []),
                correct_answer=q_dict.get("correct_answer", ""),
                explanation=q_dict.get("explanation", ""),
                canonical_skill_id=canonical_id,
                skill=skill_name,
                topic=topic_str,
                concept=q_dict.get("concept", "Core Concept"),
                difficulty=q_dict.get("difficulty", diff),
                why_the_question_is_relevant=q_dict.get("why_the_question_is_relevant"),
                question_hash=q_hash
            )
            db.add(q_record)
        db.commit()

        return AssessmentService.get_assessment(db, assessment.id, user_id=user_id)

    @staticmethod
    def generate_focused_assessment(
        db: Session,
        user_id: int,
        skill: str,
        topic: Optional[str] = None,
        num_questions: int = 10,
        difficulty: Optional[str] = None
    ) -> AssessmentResponse:
        """Generate comprehensive focused assessment (10 questions) for a skill or topic."""
        # Re-use practice generator logic with focused_assessment mode
        canon = canonicalize_skill(skill)
        skill_name = canon.display_name
        canonical_id = canon.canonical_id

        from backend.app.services.skill_topic_service import SkillTopicService
        if not difficulty or difficulty.strip().capitalize() not in ("Beginner", "Intermediate", "Advanced"):
            diff = SkillTopicService.compute_adaptive_difficulty(db, user_id, canonical_id, topic)
        else:
            diff = difficulty.strip().capitalize()

        active_jd = JobService.get_active_target_job(db, user_id)
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        target_role = (active_jd.title if active_jd and active_jd.title else None) or (profile.target_role if profile and profile.target_role else None) or "Candidate"

        topic_str = topic.strip() if (topic and topic.strip()) else f"{skill_name} Comprehensive"
        allocation = [{
            "skill": skill_name,
            "canonical_id": canonical_id,
            "difficulty": diff,
            "topic": topic_str,
            "reason": f"Focused assessment on {topic_str}"
        }]

        payload = {
            "role": target_role,
            "target_skill": skill_name,
            "target_topic": topic_str,
            "num_questions": num_questions,
            "difficulty": diff,
            "skill_allocation": allocation,
            "excluded_questions": [],
            "excluded_concepts": [],
            "focused_assessment_mode": True
        }

        try:
            ai_response: AssessmentGenerationResponse = AIGateway.execute(
                db=db,
                user_id=user_id,
                operation_type="ASSESSMENT_QUESTION_GENERATION",
                payload=payload,
                response_model=AssessmentGenerationResponse,
                force_refresh=True
            )
        except Exception as e:
            logger.error(f"Foundry focused assessment generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to generate focused assessment right now. Please try again."
            )

        raw_questions = ai_response.questions or []
        valid_questions = []
        for q in raw_questions:
            is_valid, _ = _validate_question_quality(q)
            if is_valid:
                valid_questions.append(q)

        if not valid_questions:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Focused assessment question quality validation check failed. Please retry."
            )

        questions_list = [q.model_dump() for q in valid_questions[:num_questions]]
        skill_record = SkillService.get_or_create_skill(db, skill_name, canon.category)

        title_str = f"Focused Assessment: {skill_name} — {topic_str}" if topic else f"Focused Assessment: {skill_name}"
        assessment = Assessment(
            candidate_id=user_id,
            job_id=None,
            skill_id=skill_record.id,
            canonical_skill_id=canonical_id,
            title=title_str,
            role=skill_name,
            difficulty=diff,
            question_count=len(questions_list),
            status="pending",
            assessment_mode="focused_assessment",
            topic=topic_str if topic else None,
            questions_json=questions_list,
            metadata_json={
                "is_focused_assessment": True,
                "skill": skill_name,
                "canonical_id": canonical_id,
                "topic": topic_str,
                "overview": ai_response.overview,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        for q_dict in questions_list:
            q_hash = _compute_question_hash(q_dict.get("question", ""))
            q_record = AssessmentQuestion(
                assessment_id=assessment.id,
                question=q_dict.get("question"),
                options=q_dict.get("options", []),
                correct_answer=q_dict.get("correct_answer", ""),
                explanation=q_dict.get("explanation", ""),
                canonical_skill_id=canonical_id,
                skill=skill_name,
                topic=topic_str,
                concept=q_dict.get("concept", "Core Concept"),
                difficulty=q_dict.get("difficulty", diff),
                why_the_question_is_relevant=q_dict.get("why_the_question_is_relevant"),
                question_hash=q_hash
            )
            db.add(q_record)
        db.commit()

        return AssessmentService.get_assessment(db, assessment.id, user_id=user_id)

