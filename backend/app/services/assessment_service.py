from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
import difflib

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
from backend.app.schemas.ai import AssessmentGenerationResponse, AssessmentResultAnalysisResponse
from backend.app.schemas.assessment import (
    AssessmentResponse, AssessmentQuestionSchema,
    AssessmentResultResponse, QuestionResultDetail,
    AssessmentHistoryItem
)
from backend.app.core.logging import logger


class AssessmentService:
    @staticmethod
    def list_assessments(db: Session, user_id: int) -> List[Assessment]:
        """List active personalized assessments for the candidate."""
        return (
            db.query(Assessment)
            .filter((Assessment.candidate_id == user_id) | (Assessment.candidate_id.is_(None)))
            .order_by(Assessment.created_at.desc())
            .all()
        )

    @staticmethod
    def get_assessment(db: Session, assessment_id: int) -> AssessmentResponse:
        """Serve public assessment questions to candidate, omitting correct answers and explanations."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        # Try to load from assessment_questions table first, fallback to questions_json
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
            questions=public_questions,
            created_at=assessment.created_at
        )

    @staticmethod
    def generate_personalized_assessment(
        db: Session,
        user_id: int,
        role: str,
        resume_text: Optional[str] = None,
        jd_text: Optional[str] = None,
        num_questions: int = 5
    ) -> AssessmentResponse:
        """Dynamically generate a personalized assessment using Azure AI Foundry.
        ZERO PREDEFINED QUESTIONS. Strictly grounded in candidate resume + JD + role + history.
        """
        latest_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.version.desc(), Resume.id.desc())
            .first()
        )
        latest_jd = (
            db.query(JobDescription)
            .filter(JobDescription.user_id == user_id)
            .order_by(JobDescription.created_at.desc(), JobDescription.id.desc())
            .first()
        )

        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        logger.info(
            f"[ASSESSMENT] candidate_id={user_id} "
            f"profile_id={profile.id if profile else None} "
            f"active_resume_id={latest_resume.id if latest_resume else None} "
            f"active_resume_version={latest_resume.version if latest_resume else None} "
            f"resume_exists={bool(latest_resume and latest_resume.raw_text)} "
            f"resume_intelligence_exists={bool(latest_resume and latest_resume.parsed_data)} "
            f"job_description_id={latest_jd.id if latest_jd else None} "
            f"job_description_exists={bool(latest_jd and latest_jd.raw_text)}"
        )

        # 1. Strict Validation: Candidate must have both resume and job description (Requirement 10)
        final_resume = (resume_text or (latest_resume.raw_text if latest_resume else "")).strip()
        final_jd = (jd_text or (latest_jd.raw_text if latest_jd else "")).strip()

        if not final_resume or not final_jd:
            missing = []
            if not final_resume:
                missing.append("resume")
            if not final_jd:
                missing.append("job description")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Please upload your {' and '.join(missing)} before generating a personalized assessment."
            )

        # 2. Extract Candidate Profile details
        student_skills = db.query(StudentSkill).filter(StudentSkill.user_id == user_id).all()
        candidate_skills = [sk.skill.name for sk in student_skills if sk.skill]

        candidate_projects = []
        candidate_experience = []
        candidate_education = []
        candidate_certifications = []

        if latest_resume and latest_resume.parsed_data:
            p_data = latest_resume.parsed_data
            candidate_projects = [p.get("name") for p in p_data.get("projects", []) if p.get("name")]
            candidate_experience = p_data.get("experience", [])
            candidate_education = p_data.get("education", [])
            candidate_certifications = p_data.get("certifications", [])
            # Also merge skills if not yet registered in student_skills
            for s in p_data.get("skills", []):
                s_name = s.get("name")
                if s_name and s_name not in candidate_skills:
                    candidate_skills.append(s_name)

        # 3. Extract Job Description requirements
        required_skills = []
        preferred_skills = []
        responsibilities = []
        if latest_jd and latest_jd.parsed_data:
            j_data = latest_jd.parsed_data
            required_skills = [r.get("name") for r in j_data.get("required_skills", []) if r.get("name")]
            preferred_skills = [r.get("name") for r in j_data.get("preferred_skills", []) if r.get("name")]
            responsibilities = j_data.get("key_responsibilities", [])

        # 4. Compute Candidate vs JD Skill Gaps
        identified_gaps = [r for r in required_skills if r not in candidate_skills]

        # 5. Query Previous Assessment History for Adaptive Difficulty & Weakness Context
        prev_attempts = (
            db.query(AssessmentAttempt)
            .filter(AssessmentAttempt.user_id == user_id)
            .order_by(AssessmentAttempt.completed_at.desc())
            .limit(5)
            .all()
        )
        prev_scores = [a.score_percentage for a in prev_attempts if a.score_percentage is not None]
        avg_prev_score = round(sum(prev_scores) / len(prev_scores), 1) if prev_scores else None

        # Adaptive difficulty (Requirement 26)
        if avg_prev_score is not None:
            if avg_prev_score >= 80.0:
                difficulty = "Advanced"
            elif avg_prev_score < 60.0:
                difficulty = "Beginner"
            else:
                difficulty = "Intermediate"
        else:
            difficulty = "Intermediate"

        prev_performance_summary = []
        for a in prev_attempts:
            summary = {
                "score": a.score_percentage,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None
            }
            if a.result_summary_json:
                summary["weaknesses"] = a.result_summary_json.get("weaknesses", [])
                summary["strengths"] = a.result_summary_json.get("strengths", [])
            prev_performance_summary.append(summary)

        # 6. Question & Concept Repetition Prevention (Requirement 24)
        # Fetch previous question texts and concepts for this candidate
        past_questions_query = (
            db.query(AssessmentQuestion.question, AssessmentQuestion.concept)
            .join(Assessment, AssessmentQuestion.assessment_id == Assessment.id)
            .filter(Assessment.candidate_id == user_id)
            .order_by(AssessmentQuestion.id.desc())
            .limit(50)
            .all()
        )
        excluded_questions = [row[0] for row in past_questions_query if row[0]]
        excluded_concepts = list({row[1] for row in past_questions_query if row[1]})

        # 7. Assemble context payload for Azure AI Foundry
        payload = {
            "role": role,
            "resume": final_resume,
            "job_description": final_jd,
            "num_questions": num_questions,
            "difficulty": difficulty,
            "candidate_skills": candidate_skills,
            "candidate_projects": candidate_projects,
            "candidate_experience": candidate_experience[:4],
            "candidate_education": candidate_education[:2],
            "candidate_certifications": candidate_certifications[:3],
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "responsibilities": responsibilities[:4],
            "identified_gaps": identified_gaps,
            "previous_score": avg_prev_score,
            "previous_performance": prev_performance_summary,
            "excluded_questions": excluded_questions[:15],
            "excluded_concepts": excluded_concepts[:20]
        }

        # 8. Invoke Azure AI Foundry via AIGateway (no cache for questions)
        ai_response: AssessmentGenerationResponse = AIGateway.execute(
            db=db,
            user_id=user_id,
            operation_type="ASSESSMENT_QUESTION_GENERATION",
            payload=payload,
            response_model=AssessmentGenerationResponse,
            force_refresh=True
        )

        generated_questions = ai_response.questions or []
        if not generated_questions:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to generate your personalized assessment right now. Please try again."
            )

        # 9. Verify Duplicate Prevention & Concept Collision Filter
        filtered_questions = []
        seen_stems: Set[str] = set()
        seen_concepts: Set[str] = set()

        for q in generated_questions:
            q_text = q.question.strip()
            q_stem_lower = q_text.lower()
            q_concept = (getattr(q, "concept", None) or "Core Concept").strip()
            q_concept_lower = q_concept.lower()

            # Check for intra-batch duplicate question stem or concept
            if q_stem_lower in seen_stems or (q_concept_lower != "core concept" and q_concept_lower in seen_concepts):
                logger.warning(f"Detected intra-batch duplicate stem or concept: {q_concept} / {q_text[:40]}")
                continue

            # Check for match against previously asked questions
            is_dup = False
            for past_q in excluded_questions:
                similarity = difflib.SequenceMatcher(None, q_stem_lower, past_q.lower()).ratio()
                if similarity > 0.85:
                    is_dup = True
                    logger.warning(f"Detected duplicate question with similarity {similarity:.2f}: {q_text[:60]}")
                    break

            if not is_dup:
                for past_c in excluded_concepts:
                    if q_concept_lower != "core concept" and q_concept_lower == past_c.lower():
                        is_dup = True
                        logger.warning(f"Detected past duplicate concept: {q_concept}")
                        break

            if not is_dup or len(filtered_questions) < 2:
                seen_stems.add(q_stem_lower)
                if q_concept_lower != "core concept":
                    seen_concepts.add(q_concept_lower)
                filtered_questions.append(q)

        questions_list = [q.model_dump() for q in filtered_questions]

        # 10. Store Assessment in Database (Requirement 15)
        assessment = Assessment(
            candidate_id=user_id,
            job_id=latest_jd.id if latest_jd else None,
            skill_id=None,
            title=ai_response.title or f"Personalized Assessment for {role}",
            role=role,
            difficulty=difficulty,
            question_count=len(questions_list),
            status="pending",
            questions_json=questions_list,
            metadata_json={
                "overview": ai_response.overview,
                "total_generated": len(questions_list),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "identified_gaps": identified_gaps
            }
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # 11. Store Every Generated Question in assessment_questions table (Requirement 16)
        for idx, q_dict in enumerate(questions_list, start=1):
            q_record = AssessmentQuestion(
                assessment_id=assessment.id,
                question=q_dict.get("question"),
                options=q_dict.get("options", []),
                correct_answer=q_dict.get("correct_answer", ""),
                explanation=q_dict.get("explanation", ""),
                skill=q_dict.get("skill"),
                topic=q_dict.get("topic"),
                concept=q_dict.get("concept", "Core Concept"),
                difficulty=q_dict.get("difficulty", difficulty),
                why_the_question_is_relevant=q_dict.get("why_the_question_is_relevant")
            )
            db.add(q_record)
        db.commit()

        return AssessmentService.get_assessment(db, assessment.id)

    @staticmethod
    def submit_assessment(
        db: Session,
        user_id: int,
        assessment_id: int,
        submitted_answers: Dict[str, str]
    ) -> AssessmentResultResponse:
        """Deterministically score assessment, persist every answer, and trigger AI Result Analysis."""
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        # Load questions from assessment_questions table
        db_questions = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.id.asc())
            .all()
        )

        # Fallback to questions_json if not found in db_questions
        questions_to_score = []
        if db_questions:
            for q in db_questions:
                questions_to_score.append({
                    "id": q.id,
                    "question": q.question,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
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

        # 1. Deterministic Scoring & Per-Skill Tracking (Requirement 18)
        correct_count = 0
        details: List[QuestionResultDetail] = []
        strengths: List[str] = []
        weaknesses: List[str] = []
        topics_to_improve: List[str] = []
        per_skill_stats: Dict[str, Dict[str, int]] = {}

        # Clean existing answers if re-submitting
        db.query(AssessmentAnswer).filter(
            AssessmentAnswer.assessment_id == assessment_id,
            AssessmentAnswer.candidate_id == user_id
        ).delete()

        for q in questions_to_score:
            q_id_str = str(q["id"])
            correct_ans = str(q["correct_answer"]).strip()
            # Match by question ID or index
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

            # 2. Store Every Answer in assessment_answers Table (Requirement 17)
            if q.get("_db_obj"):
                ans_record = AssessmentAnswer(
                    assessment_id=assessment.id,
                    question_id=q["_db_obj"].id,
                    candidate_id=user_id,
                    selected_answer=user_ans if user_ans else "Unanswered",
                    correct_answer=correct_ans,
                    is_correct=is_correct,
                    answered_at=datetime.now(timezone.utc)
                )
                db.add(ans_record)

            details.append(QuestionResultDetail(
                question_id=q["id"],
                question=q["question"],
                selected_answer=user_ans if user_ans else "None",
                correct_answer=correct_ans,
                is_correct=is_correct,
                explanation=q["explanation"],
                topic=q["topic"],
                concept=q.get("concept"),
                skill=s_name,
                why_the_question_is_relevant=q["why_the_question_is_relevant"]
            ))

        score_percentage = round((correct_count / total_questions) * 100.0, 1)
        passed = score_percentage >= 60.0

        if score_percentage >= 80.0:
            demonstrated_level = "Advanced"
        elif score_percentage >= 60.0:
            demonstrated_level = "Intermediate"
        else:
            demonstrated_level = "Beginner"

        if score_percentage >= 75.0:
            new_confidence = "High"
        elif score_percentage >= 50.0:
            new_confidence = "Medium"
        else:
            new_confidence = "Low"

        # 3. Persist Per-Skill Scores Directly into StudentSkill Records
        per_skill_scores: Dict[str, float] = {}
        for s_name, stats in per_skill_stats.items():
            skill_score = round((stats["correct"] / max(stats["total"], 1)) * 100.0, 1)
            per_skill_scores[s_name] = skill_score

            # Standardize or insert Skill
            skill = db.query(Skill).filter(Skill.name.ilike(s_name)).first()
            if not skill:
                skill = Skill(name=s_name, category="Technical")
                db.add(skill)
                db.flush()

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

            # Check GitHub evidence for this skill
            has_github = db.query(Evidence).filter(
                Evidence.user_id == user_id,
                Evidence.skill_id == skill.id,
                Evidence.type == "GitHub"
            ).count() > 0
            claimed = bool(student_skill.is_claimed)

            # Calibrate demonstrated level for this skill
            if skill_score >= 80.0:
                s_dem = "Advanced"
            elif skill_score >= 60.0:
                s_dem = "Intermediate"
            else:
                s_dem = "Beginner"

            # Calibrate confidence based on rules:
            # High: Assessment >= 75% OR (Assessment >= 65% and has_github and claimed)
            # Medium: Assessment between 50-74%
            # Low: Assessment < 50%
            if skill_score >= 75.0 or (skill_score >= 65.0 and has_github and claimed):
                s_conf = "High"
            elif skill_score >= 50.0:
                s_conf = "Medium"
            else:
                s_conf = "Low"

            student_skill.assessment_score = skill_score
            student_skill.demonstrated_level = s_dem
            student_skill.confidence = s_conf
            student_skill.last_updated = datetime.now(timezone.utc)

        # 3. AI Result Analysis via Azure AI Foundry (Requirement 19)
        latest_resume = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.id.desc()).first()
        resume_text = latest_resume.raw_text if latest_resume and latest_resume.raw_text else ""
        latest_jd = db.query(JobDescription).filter(JobDescription.user_id == user_id).order_by(JobDescription.id.desc()).first()
        jd_text = latest_jd.raw_text if latest_jd and latest_jd.raw_text else ""
        student_skills = db.query(StudentSkill).filter(StudentSkill.user_id == user_id).all()
        candidate_skills = [sk.skill.name for sk in student_skills if sk.skill]

        ai_payload = {
            "role": assessment.role or "Software Engineer",
            "resume": resume_text,
            "job_description": jd_text,
            "candidate_skills": candidate_skills,
            "questions": [{k: v for k, v in q.items() if k != "_db_obj"} for q in questions_to_score],
            "answers": submitted_answers,
            "score_percentage": score_percentage,
            "correct_count": correct_count,
            "total_questions": total_questions
        }

        ai_analysis: AssessmentResultAnalysisResponse = AIGateway.execute(
            db=db,
            user_id=user_id,
            operation_type="ASSESSMENT_RESULT_ANALYSIS",
            payload=ai_payload,
            response_model=AssessmentResultAnalysisResponse,
            force_refresh=True
        )

        final_strengths = ai_analysis.strengths if ai_analysis.strengths else strengths
        final_weaknesses = ai_analysis.weaknesses if ai_analysis.weaknesses else weaknesses
        final_skill_gaps = ai_analysis.skill_gaps if ai_analysis.skill_gaps else list(set(weaknesses))
        final_topics = ai_analysis.topics_to_improve if ai_analysis.topics_to_improve else topics_to_improve
        final_priority = ai_analysis.priority_areas if ai_analysis.priority_areas else [w for w in weaknesses]
        final_plan = ai_analysis.improvement_plan if ai_analysis.improvement_plan else []

        result_summary = {
            "strengths": final_strengths,
            "weaknesses": final_weaknesses,
            "skill_gaps": final_skill_gaps,
            "topics_to_improve": final_topics,
            "priority_areas": final_priority,
            "improvement_plan": final_plan,
            "reassessment_recommendations": ai_analysis.reassessment_recommendations,
            "summary_feedback": ai_analysis.summary_feedback,
            "per_skill_scores": per_skill_scores,
            "details": [d.model_dump() for d in details]
        }

        # 4. Save Attempt & Analysis in Database (Requirement 20)
        attempt = AssessmentAttempt(
            user_id=user_id,
            assessment_id=assessment.id,
            score_percentage=score_percentage,
            total_questions=total_questions,
            correct_count=correct_count,
            answers_json=submitted_answers,
            result_summary_json=result_summary,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(attempt)

        # Update Assessment Status to completed
        assessment.status = "completed"
        db.commit()
        db.refresh(attempt)

        skill_name = assessment.skill.name if assessment.skill else (assessment.role or "Personalized Assessment")
        return AssessmentResultResponse(
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            skill_id=assessment.skill_id,
            skill_name=skill_name,
            role=assessment.role,
            score_percentage=score_percentage,
            total_questions=total_questions,
            correct_count=correct_count,
            passed=passed,
            new_confidence=new_confidence,
            new_demonstrated_level=demonstrated_level,
            per_skill_scores=per_skill_scores,
            strengths=final_strengths,
            weaknesses=final_weaknesses,
            skill_gaps=final_skill_gaps,
            topics_to_improve=final_topics,
            priority_areas=final_priority,
            improvement_plan=final_plan,
            reassessment_recommendations=ai_analysis.reassessment_recommendations,
            summary_feedback=ai_analysis.summary_feedback,
            details=details,
            completed_at=attempt.completed_at
        )

    @staticmethod
    def get_assessment_result(db: Session, user_id: int, assessment_id: int) -> AssessmentResultResponse:
        """Fetch saved assessment result from database. Persists across browser refreshes (Requirement 30)."""
        attempt = (
            db.query(AssessmentAttempt)
            .filter(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.user_id == user_id
            )
            .order_by(AssessmentAttempt.completed_at.desc())
            .first()
        )
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No completed assessment attempt found for this ID."
            )

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        res_sum = attempt.result_summary_json or {}

        details = []
        raw_details = res_sum.get("details", [])
        if raw_details:
            details = [QuestionResultDetail.model_validate(d) for d in raw_details]
        else:
            # Reconstruct from assessment_answers table
            answers = (
                db.query(AssessmentAnswer)
                .filter(
                    AssessmentAnswer.assessment_id == assessment_id,
                    AssessmentAnswer.candidate_id == user_id
                )
                .all()
            )
            for a in answers:
                q_obj = a.question_rel
                details.append(QuestionResultDetail(
                    question_id=a.question_id,
                    question=q_obj.question if q_obj else "Question",
                    selected_answer=a.selected_answer,
                    correct_answer=a.correct_answer,
                    is_correct=a.is_correct,
                    explanation=q_obj.explanation if q_obj else "",
                    topic=q_obj.topic if q_obj else None,
                    concept=q_obj.concept if q_obj else None,
                    skill=q_obj.skill if q_obj else None,
                    why_the_question_is_relevant=q_obj.why_the_question_is_relevant if q_obj else None
                ))

        score_pct = attempt.score_percentage
        passed = score_pct >= 60.0
        demonstrated = "Advanced" if score_pct >= 80.0 else ("Intermediate" if score_pct >= 60.0 else "Beginner")
        confidence = "High" if score_pct >= 75.0 else ("Medium" if score_pct >= 50.0 else "Low")
        per_skill_scores = res_sum.get("per_skill_scores", {})

        skill_name = assessment.role if assessment else "Personalized Assessment"
        return AssessmentResultResponse(
            attempt_id=attempt.id,
            assessment_id=assessment_id,
            skill_id=assessment.skill_id if assessment else None,
            skill_name=skill_name,
            role=assessment.role if assessment else "Target Role",
            score_percentage=attempt.score_percentage,
            total_questions=attempt.total_questions,
            correct_count=attempt.correct_count,
            passed=passed,
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
    def get_assessment_history(db: Session, user_id: int) -> List[AssessmentHistoryItem]:
        """Fetch complete candidate assessment history (Requirement 22)."""
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
            difficulty = assessment.difficulty if assessment else "Intermediate"
            res_sum = att.result_summary_json or {}

            history.append(AssessmentHistoryItem(
                attempt_id=att.id,
                assessment_id=att.assessment_id,
                role=role,
                difficulty=difficulty,
                score_percentage=att.score_percentage,
                total_questions=att.total_questions,
                correct_count=att.correct_count,
                passed=att.score_percentage >= 60.0,
                strengths=res_sum.get("strengths", []),
                weaknesses=res_sum.get("weaknesses", []),
                skill_gaps=res_sum.get("skill_gaps", []),
                summary_feedback=res_sum.get("summary_feedback"),
                improvement_plan=res_sum.get("improvement_plan", []),
                completed_at=att.completed_at
            ))
        return history
