from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.evidence import Evidence
from backend.app.models.profile import StudentProfile
from backend.app.models.assessment import Assessment
from backend.app.schemas.skill import (
    SkillMatrixItem, SkillGapResponse, RecommendedActionResponse,
    CandidateJDSkillItem, CandidateJDComparisonResponse
)
from backend.app.models.job import JobDescription
from backend.app.models.resume import Resume


class SkillService:
    @staticmethod
    def get_skill_matrix(db: Session, user_id: int) -> List[SkillMatrixItem]:
        """Comparison of Claimed vs GitHub Evidence vs Objective Assessment Score."""
        student_skills = (
            db.query(StudentSkill)
            .join(Skill, StudentSkill.skill_id == Skill.id)
            .filter(StudentSkill.user_id == user_id)
            .all()
        )

        matrix: List[SkillMatrixItem] = []
        for ss in student_skills:
            skill = ss.skill

            # Check GitHub evidence for this skill
            has_github = (
                db.query(Evidence)
                .filter(
                    Evidence.user_id == user_id,
                    Evidence.skill_id == skill.id,
                    Evidence.type == "GitHub"
                )
                .count() > 0
            )

            # Confidence & Status calculation
            score = ss.assessment_score
            claimed = bool(ss.is_claimed)
            
            # Confidence logic:
            # High: Assessment >= 75% OR (Assessment >= 65% and has_github and claimed)
            # Medium: Assessment between 50-74% OR (claimed and has_github without assessment)
            # Low: Assessment < 50% OR claimed without evidence/assessment
            # None: neither claimed nor assessed
            if score is not None:
                if score >= 75.0 or (score >= 65.0 and has_github and claimed):
                    confidence = "High"
                    status = "Ready"
                elif score >= 50.0:
                    confidence = "Medium"
                    status = "Needs Practice"
                else:
                    confidence = "Low"
                    status = "Critical Gap"
            else:
                if claimed and has_github:
                    confidence = "Medium"
                    status = "Unassessed (Has Evidence)"
                elif claimed:
                    confidence = "Low"
                    status = "Unassessed (Claim Only)"
                else:
                    confidence = "None"
                    status = "Required Missing"

            if score is not None and not ss.demonstrated_level:
                ss.demonstrated_level = "Advanced" if score >= 80.0 else ("Intermediate" if score >= 60.0 else "Beginner")

            # Update student skill confidence if changed
            if ss.confidence != confidence:
                ss.confidence = confidence
                ss.last_updated = datetime.now(timezone.utc)

            matrix.append(SkillMatrixItem(
                skill_id=skill.id,
                skill_name=skill.name,
                category=skill.category,
                claimed=claimed,
                github_evidence=has_github,
                assessment_score=score,
                demonstrated_level=ss.demonstrated_level,
                confidence=confidence,
                status=status,
                evidence_count=ss.evidence_count
            ))

        db.commit()
        return matrix

    @staticmethod
    def calculate_skill_gaps(db: Session, user_id: int) -> SkillGapResponse:
        """Identification of verified strengths and gaps."""
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        target_role = profile.target_role if profile else "Software Engineer"

        matrix = SkillService.get_skill_matrix(db, user_id)

        strong_skills = [item.skill_name for item in matrix if item.confidence == "High"]
        moderate_skills = [item.skill_name for item in matrix if item.confidence == "Medium"]
        weak_skills = [item.skill_name for item in matrix if item.confidence == "Low"]
        critical_gaps = [item.skill_name for item in matrix if item.status in ["Critical Gap", "Required Missing"]]

        return SkillGapResponse(
            target_role=target_role,
            total_skills_tracked=len(matrix),
            strong_skills=strong_skills,
            moderate_skills=moderate_skills,
            weak_skills=weak_skills,
            critical_gaps=critical_gaps,
            matrix=matrix
        )

    @staticmethod
    def compare_candidate_vs_jd(db: Session, user_id: int) -> CandidateJDComparisonResponse:
        """Compare candidate evidence against the JD with exact categories:
        - Strong / Evidence Found
        - Needs Assessment
        - Skill Gap
        - Unknown
        - Not Relevant
        Never claims an unknown skill is possessed by the candidate.
        """
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        target_role = profile.target_role if profile else "Software Engineer"

        # 1. Fetch latest JD requirements
        latest_jd = db.query(JobDescription).filter(JobDescription.user_id == user_id).order_by(JobDescription.id.desc()).first()
        jd_skills_dict = {}

        if latest_jd and latest_jd.parsed_data:
            for req in latest_jd.parsed_data.get("required_skills", []):
                name = req.get("name", "").strip()
                if name:
                    jd_skills_dict[name.lower()] = {
                        "name": name,
                        "category": req.get("category", "Programming"),
                        "importance": "Required"
                    }
            for pref in latest_jd.parsed_data.get("preferred_skills", []):
                name = pref.get("name", "").strip()
                if name and name.lower() not in jd_skills_dict:
                    jd_skills_dict[name.lower()] = {
                        "name": name,
                        "category": pref.get("category", "Programming"),
                        "importance": "Preferred"
                    }
        else:
            # Baseline requirements for target role
            baseline = [
                ("Python", "Programming", "Required"),
                ("SQL", "Database", "Required"),
                ("FastAPI", "Framework", "Required"),
                ("System Design", "CS Fundamentals", "Required"),
                ("Docker", "DevOps", "Preferred"),
                ("Git", "Tools", "Required")
            ]
            for name, cat, imp in baseline:
                jd_skills_dict[name.lower()] = {"name": name, "category": cat, "importance": imp}

        # 2. Fetch candidate's verified skills & assessment scores
        matrix = SkillService.get_skill_matrix(db, user_id)
        candidate_skills_map = {m.skill_name.lower(): m for m in matrix}

        items: List[CandidateJDSkillItem] = []
        evidence_found: List[str] = []
        needs_assessment: List[str] = []
        skill_gaps: List[str] = []
        unknown: List[str] = []

        for key, jd_meta in jd_skills_dict.items():
            name = jd_meta["name"]
            category = jd_meta["category"]
            importance = jd_meta["importance"]

            m_item = candidate_skills_map.get(key)
            if m_item:
                score = m_item.assessment_score
                has_github = m_item.github_evidence
                is_claimed = m_item.claimed

                if score is not None:
                    if score >= 65.0:
                        status = "Evidence Found"
                        notes = f"Objective assessment verified ({score}% score)."
                        evidence_found.append(name)
                    elif score < 50.0:
                        status = "Skill Gap"
                        notes = f"Assessment score was {score}% (below 50% threshold)."
                        skill_gaps.append(name)
                    else:
                        status = "Needs Assessment"
                        notes = f"Moderate assessment score ({score}%). Practice recommended."
                        needs_assessment.append(name)
                else:
                    if has_github:
                        status = "Needs Assessment"
                        notes = "GitHub code evidence exists; pending objective assessment."
                        needs_assessment.append(name)
                    elif is_claimed:
                        status = "Needs Assessment"
                        notes = "Claimed on resume, but no objective assessment completed."
                        needs_assessment.append(name)
                    else:
                        if importance == "Required":
                            status = "Skill Gap"
                            notes = "Required by JD, but candidate has provided zero evidence."
                            skill_gaps.append(name)
                        else:
                            status = "Unknown"
                            notes = "Preferred technology not evidenced by candidate."
                            unknown.append(name)

                items.append(CandidateJDSkillItem(
                    skill_name=name,
                    category=category,
                    importance=importance,
                    candidate_status=status,
                    evidence_source="Assessment/Resume" if score is not None else ("GitHub" if has_github else "Resume Claim"),
                    assessment_score=score,
                    notes=notes
                ))
            else:
                # Skill not present in candidate's tracked profile at all
                if importance == "Required":
                    status = "Skill Gap"
                    notes = f"Required by {target_role} JD. No candidate evidence on file."
                    skill_gaps.append(name)
                else:
                    status = "Unknown"
                    notes = "Preferred JD skill with unverified proficiency."
                    unknown.append(name)

                items.append(CandidateJDSkillItem(
                    skill_name=name,
                    category=category,
                    importance=importance,
                    candidate_status=status,
                    evidence_source="None",
                    assessment_score=None,
                    notes=notes
                ))

        total_jd_skills = len(jd_skills_dict)
        match_percentage = round((len(evidence_found) / max(total_jd_skills, 1)) * 100.0, 1)

        return CandidateJDComparisonResponse(
            target_role=target_role,
            total_jd_skills=total_jd_skills,
            matched_skills_count=len(evidence_found),
            match_percentage=match_percentage,
            evidence_found=evidence_found,
            needs_assessment=needs_assessment,
            skill_gaps=skill_gaps,
            unknown=unknown,
            items=items
        )

    @staticmethod
    def get_recommended_next_action(db: Session, user_id: int) -> RecommendedActionResponse:
        """Calculate the single most valuable next action for the student."""
        matrix = SkillService.get_skill_matrix(db, user_id)

        # 1. If no skills tracked at all, recommend uploading resume
        if not matrix:
            return RecommendedActionResponse(
                action_type="RESUME",
                title="Upload Your Resume",
                description="Upload your resume (PDF/DOCX) to automatically extract your skills and start gap analysis.",
                reason="No skills currently on file.",
                skill_name=None,
                target_route="Resume"
            )

        # 2. Check for critical gaps with low assessment score (< 50%)
        critical_tested_gaps = [m for m in matrix if m.assessment_score is not None and m.assessment_score < 50.0]
        if critical_tested_gaps:
            top_gap = critical_tested_gaps[0]
            return RecommendedActionResponse(
                action_type="LEARNING",
                title=f"Review & Practice: {top_gap.skill_name}",
                description=f"Your assessment score for {top_gap.skill_name} was {top_gap.assessment_score}%. Follow the targeted improvement plan.",
                reason=f"{top_gap.skill_name} is currently a Critical Gap.",
                skill_name=top_gap.skill_name,
                target_route="Personalized Improvement Plan"
            )

        # 3. Check for claimed skills that are unassessed
        unassessed_skills = [m for m in matrix if m.assessment_score is None and m.claimed]
        if unassessed_skills:
            top_unassessed = unassessed_skills[0]
            return RecommendedActionResponse(
                action_type="ASSESSMENT",
                title=f"Take Personalized Assessment on {top_unassessed.skill_name}",
                description=f"Validate your claimed {top_unassessed.skill_name} proficiency with an objective personalized assessment.",
                reason="Claimed in resume, but missing objective assessment proof.",
                skill_name=top_unassessed.skill_name,
                target_route="Personalized Assessment"
            )

        # 4. Check for medium confidence skills (50-74%) -> Recommend taking personalized assessment
        moderate_skills = [m for m in matrix if m.confidence == "Medium"]
        if moderate_skills:
            target_skill = moderate_skills[0]
            return RecommendedActionResponse(
                action_type="ASSESSMENT",
                title=f"Reassess {target_skill.skill_name}",
                description=f"Complete a personalized assessment to elevate your demonstrated confidence from Medium to High.",
                reason=f"{target_skill.skill_name} has moderate confidence.",
                skill_name=target_skill.skill_name,
                target_route="Personalized Assessment"
            )

        # 5. Otherwise, recommend reviewing personalized improvement plan
        return RecommendedActionResponse(
            action_type="IMPROVEMENT_PLAN",
            title="Review Personalized Improvement Plan",
            description="Follow your customized skill plan and practice target MCQ assessments to ensure total role readiness.",
            reason="Core skills verified. Maintain continuous placement readiness.",
            skill_name=None,
            target_route="Personalized Improvement Plan"
        )
