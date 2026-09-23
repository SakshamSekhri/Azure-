from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.models.profile import StudentProfile
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.evidence import Evidence
from backend.app.models.assessment_attempt import AssessmentAttempt
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.skill import Skill, StudentSkill
from backend.app.schemas.placement_profile import (
    PlacementProfileSchema, CandidateInfo, ProfileSkillItem
)
from backend.app.services.skill_service import SkillService
from backend.app.services.skill_canonicalizer import canonicalize_skill
from backend.app.services.job_service import JobService


class PlacementProfileService:
    """Authoritative service providing the central normalized candidate representation (Requirement 3).
    Precludes redundant, duplicate raw resume and JD queries throughout the platform.
    """

    @staticmethod
    def get_placement_profile(db: Session, user_id: int, job_id: Optional[int] = None) -> PlacementProfileSchema:
        # 1. Fetch Latest Active Job Description FIRST (Single Source of Truth for Role)
        latest_jd = JobService.get_active_target_job(db, user_id, job_id=job_id)
        has_jd = bool(latest_jd and latest_jd.raw_text and latest_jd.raw_text.strip())

        # 2. Fetch Candidate Base Info
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        active_role = (latest_jd.title if latest_jd and latest_jd.title else None) or (profile.target_role if profile and profile.target_role else None) or "Candidate"

        if not profile:
            candidate_info = CandidateInfo(
                user_id=user_id,
                name="Candidate",
                target_role=active_role,
                experience_level="Entry Level"
            )
        else:
            candidate_info = CandidateInfo(
                user_id=user_id,
                name=profile.name or "Candidate",
                target_role=active_role,
                experience_level=profile.experience_level or "Entry Level",
                college=profile.college,
                degree=profile.degree,
                graduation_year=profile.graduation_year,
                github_username=profile.github_username
            )

        # 3. Fetch Latest Active Resume
        latest_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.version.desc(), Resume.id.desc())
            .first()
        )
        has_resume = bool(latest_resume and latest_resume.raw_text and latest_resume.raw_text.strip())

        # 4. Extract Structured Resume Intelligence
        projects: List[Dict[str, Any]] = []
        experience: List[Dict[str, Any]] = []
        education: List[Dict[str, Any]] = []
        certifications: List[Dict[str, Any]] = []

        if latest_resume and latest_resume.parsed_data:
            p_data = latest_resume.parsed_data
            projects = p_data.get("projects", [])
            experience = p_data.get("experience", [])
            education = p_data.get("education", [])
            certifications = p_data.get("certifications", [])

        # 5. Extract GitHub Evidence
        github_evs = (
            db.query(Evidence)
            .filter(Evidence.user_id == user_id, Evidence.type == "GitHub")
            .order_by(Evidence.created_at.desc())
            .all()
        )
        github_evidence = [
            {
                "title": ev.title,
                "description": ev.description,
                "url": ev.url,
                "metadata": ev.metadata_json
            }
            for ev in github_evs
        ]

        # 6. Fetch Skill Matrix with Canonical Mapping
        matrix = SkillService.get_skill_matrix(db, user_id)
        matrix_map: Dict[str, Any] = {}
        skill_scores: Dict[str, float] = {}

        claimed_skills: List[ProfileSkillItem] = []
        verified_skills: List[ProfileSkillItem] = []

        for m in matrix:
            c_id = m.canonical_id or canonicalize_skill(m.skill_name).canonical_id
            item = ProfileSkillItem(
                canonical_id=c_id,
                display_name=m.skill_name,
                category=m.category,
                claimed=m.claimed,
                demonstrated_level=m.demonstrated_level,
                confidence=m.confidence,
                assessment_score=m.assessment_score,
                evidence_count=m.evidence_count,
                github_evidence=m.github_evidence
            )
            matrix_map[c_id] = item
            if m.assessment_score is not None:
                skill_scores[c_id] = m.assessment_score

            if m.claimed:
                claimed_skills.append(item)
            if m.confidence in ("High", "Medium"):
                verified_skills.append(item)

        # 7. Extract JD Requirements & Map Gaps
        required_skills: List[ProfileSkillItem] = []
        preferred_skills: List[ProfileSkillItem] = []
        skill_gaps: List[ProfileSkillItem] = []

        if latest_jd and latest_jd.parsed_data:
            j_data = latest_jd.parsed_data
            for r in j_data.get("required_skills", []):
                name = r.get("name", "").strip()
                cat = r.get("category", "Programming")
                if not name:
                    continue
                canon = canonicalize_skill(name, cat)
                cand_item = matrix_map.get(canon.canonical_id)

                skill_item = ProfileSkillItem(
                    canonical_id=canon.canonical_id,
                    display_name=canon.display_name,
                    category=canon.category,
                    claimed=cand_item.claimed if cand_item else False,
                    confidence=cand_item.confidence if cand_item else "None",
                    assessment_score=cand_item.assessment_score if cand_item else None,
                    evidence_count=cand_item.evidence_count if cand_item else 0,
                    github_evidence=cand_item.github_evidence if cand_item else False,
                    importance="Required"
                )
                required_skills.append(skill_item)

                # Flag as gap if unevidenced or score < 50% or Low confidence
                if not cand_item or cand_item.confidence in ("Low", "None") or (cand_item.assessment_score is not None and cand_item.assessment_score < 50.0):
                    skill_gaps.append(skill_item)

            for p in j_data.get("preferred_skills", []):
                name = p.get("name", "").strip()
                cat = p.get("category", "Programming")
                if not name:
                    continue
                canon = canonicalize_skill(name, cat)
                cand_item = matrix_map.get(canon.canonical_id)

                pref_item = ProfileSkillItem(
                    canonical_id=canon.canonical_id,
                    display_name=canon.display_name,
                    category=canon.category,
                    claimed=cand_item.claimed if cand_item else False,
                    confidence=cand_item.confidence if cand_item else "None",
                    assessment_score=cand_item.assessment_score if cand_item else None,
                    evidence_count=cand_item.evidence_count if cand_item else 0,
                    github_evidence=cand_item.github_evidence if cand_item else False,
                    importance="Preferred"
                )
                preferred_skills.append(pref_item)

        # 8. Fetch Assessment History & Weak Topics
        attempts = (
            db.query(AssessmentAttempt)
            .filter(AssessmentAttempt.user_id == user_id)
            .order_by(AssessmentAttempt.completed_at.desc())
            .limit(10)
            .all()
        )
        assessment_history: List[Dict[str, Any]] = []
        for att in attempts:
            assessment_history.append({
                "attempt_id": att.id,
                "assessment_id": att.assessment_id,
                "score_percentage": att.score_percentage,
                "score": att.score_percentage,
                "total_questions": att.total_questions,
                "correct_count": att.correct_count,
                "completed_at": att.completed_at.isoformat() if att.completed_at else None,
                "summary": att.result_summary_json
            })

        # Deterministically collect weak topics from incorrect assessment answers
        incorrect_answers = (
            db.query(AssessmentAnswer)
            .join(AssessmentQuestion, AssessmentAnswer.question_id == AssessmentQuestion.id)
            .filter(AssessmentAnswer.candidate_id == user_id, AssessmentAnswer.is_correct == False)
            .order_by(AssessmentAnswer.answered_at.desc())
            .limit(20)
            .all()
        )
        weak_topics_set = set()
        for ans in incorrect_answers:
            q = ans.question_rel
            if q and q.topic:
                weak_topics_set.add(q.topic)
            if q and q.concept and q.concept.lower() != "core concept":
                weak_topics_set.add(f"{q.skill}: {q.concept}")

        return PlacementProfileSchema(
            candidate=candidate_info,
            claimed_skills=claimed_skills,
            verified_skills=verified_skills,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            skill_gaps=skill_gaps,
            projects=projects,
            experience=experience,
            education=education,
            certifications=certifications,
            github_evidence=github_evidence,
            assessment_history=assessment_history,
            skill_scores=skill_scores,
            weak_topics=list(weak_topics_set),
            active_resume_id=latest_resume.id if latest_resume else None,
            active_jd_id=latest_jd.id if latest_jd else None,
            has_resume=has_resume,
            has_jd=has_jd
        )

    @staticmethod
    def build_compact_ai_context(
        profile: PlacementProfileSchema,
        num_questions: int,
        target_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a compact, structured representation of the candidate profile
        to minimize prompt tokens and Azure credit usage (Requirement 17).
        """
        role = target_role or profile.candidate.target_role

        # Format compact projects summary (names & tech only, no wall of text)
        compact_projects = []
        for p in profile.projects[:3]:
            compact_projects.append({
                "name": p.get("name"),
                "technologies": p.get("technologies", [])
            })

        # Format compact skill gaps
        compact_gaps = [g.display_name for g in profile.skill_gaps]

        # Format claimed & verified skills
        compact_claimed = [s.display_name for s in profile.claimed_skills]
        compact_verified = [f"{s.display_name} ({s.demonstrated_level or 'Intermediate'})" for s in profile.verified_skills]
        compact_required = [r.display_name for r in profile.required_skills]

        # Calculate average previous score
        prev_scores = [h["score_percentage"] for h in profile.assessment_history if h.get("score_percentage") is not None]
        avg_prev_score = round(sum(prev_scores) / len(prev_scores), 1) if prev_scores else None

        return {
            "target_role": role,
            "experience_level": profile.candidate.experience_level,
            "num_questions": num_questions,
            "required_skills": compact_required,
            "skill_gaps": compact_gaps,
            "claimed_skills": compact_claimed,
            "verified_skills": compact_verified,
            "key_projects": compact_projects,
            "weak_topics": profile.weak_topics[:6],
            "average_previous_score": avg_prev_score,
            "per_skill_scores": profile.skill_scores
        }
