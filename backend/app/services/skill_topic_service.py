from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.assessment import Assessment
from backend.app.models.assessment_question import AssessmentQuestion
from backend.app.models.assessment_answer import AssessmentAnswer
from backend.app.models.learning_activity import LearningActivity
from backend.app.models.learning_plan import LearningPlan
from backend.app.models.job import JobDescription
from backend.app.services.skill_canonicalizer import canonicalize_skill, CanonicalSkill
from backend.app.schemas.practice import (
    TopicPerformanceItem,
    SkillFocusDetailResponse
)


# Canonical starter topics taxonomy for common engineering competencies when no historical data exists
STARTER_TOPICS_MAP: Dict[str, List[str]] = {
    "python": ["Data Structures & Collections", "Generators & Iterators", "Decorators & Metaclasses", "AsyncIO & Concurrency", "Error Handling & Context Managers"],
    "docker": ["Dockerfile Optimization & Multi-Stage", "Container Networking & Port Mapping", "Volumes & Persistent Storage", "Docker Compose Orchestration", "Security & Resource Limits"],
    "fastapi": ["Dependency Injection & Lifespans", "Pydantic Request Validation", "Async Path Operations & Concurrency", "Background Tasks & Middleware", "Authentication & Security Scopes"],
    "sql": ["Indexing & Query Execution Plans", "Joins, Aggregations & Subqueries", "ACID Transactions & Locking", "Schema Design & Normalization", "Window Functions & CTEs"],
    "postgresql": ["MVCC & Concurrency Control", "Indexing Strategies (B-Tree, GIN)", "JSONB Storage & Queries", "Connection Pooling & PgBouncer", "Partitioning & Replication"],
    "git": ["Branching, Merging & Rebase Strategies", "Conflict Resolution", "Cherry-Pick & Reflog Recovery", "Git Hooks & Submodules", "Commit Hygiene & Reset Modes"],
    "system-design": ["Horizontal vs Vertical Scaling", "Load Balancing & Reverse Proxies", "Caching Strategies & Cache Invalidation", "Message Queues & Event-Driven Architecture", "Database Sharding & Replication"],
    "kubernetes": ["Pods, Deployments & ReplicaSets", "Services, Ingress & Networking", "ConfigMaps, Secrets & Env Vars", "Resource Limits, Requests & HPA", "StatefulSets & PersistentVolumes"],
    "aws": ["EC2 & Auto Scaling Groups", "S3 Storage Classes & Policies", "IAM Roles & Least Privilege", "Lambda Serverless Architecture", "VPC, Subnets & Security Groups"],
    "azure": ["Azure App Service & Functions", "Azure Virtual Networks & NSGs", "Blob Storage & Access Tiers", "Azure Key Vault & Managed Identities", "Azure Cosmos DB Consistency Models"],
    "redis": ["In-Memory Caching & Eviction Policies", "Pub/Sub Messaging Patterns", "Data Structures (Hashes, Sorted Sets)", "Persistence (RDB vs AOF)", "Distributed Locks with Redlock"],
    "rest-api": ["HTTP Methods, Status Codes & Semantics", "Pagination, Filtering & Sorting", "Rate Limiting & Throttling", "Idempotency & Safe Methods", "API Authentication (JWT, Bearer)"]
}


class SkillTopicService:
    @staticmethod
    def compute_adaptive_difficulty(
        db: Session,
        user_id: int,
        canonical_skill_id: str,
        topic: Optional[str] = None
    ) -> str:
        """Determines adaptive difficulty based on candidate's historical performance on the skill/topic.
        Adaptive Rules:
        - Score < 50% -> Beginner
        - Score 50-74% -> Intermediate
        - Score >= 75% -> Advanced
        - Unassessed claimed -> Intermediate
        - Unassessed gap -> Beginner
        """
        # 1. Check topic-specific answers if topic is specified
        if topic and topic.strip():
            topic_clean = topic.strip().lower()
            topic_answers = (
                db.query(AssessmentAnswer.is_correct)
                .join(AssessmentQuestion, AssessmentAnswer.question_id == AssessmentQuestion.id)
                .filter(
                    AssessmentAnswer.candidate_id == user_id,
                    (AssessmentQuestion.canonical_skill_id == canonical_skill_id) | (AssessmentQuestion.skill.ilike(canonical_skill_id)),
                    func.lower(AssessmentQuestion.topic) == topic_clean
                )
                .all()
            )
            if len(topic_answers) >= 2:
                correct = sum(1 for a in topic_answers if a.is_correct)
                pct = (correct / len(topic_answers)) * 100.0
                if pct >= 75.0:
                    return "Advanced"
                elif pct >= 50.0:
                    return "Intermediate"
                else:
                    return "Beginner"

        # 2. Check skill-level answers across all topics
        skill_answers = (
            db.query(AssessmentAnswer.is_correct)
            .join(AssessmentQuestion, AssessmentAnswer.question_id == AssessmentQuestion.id)
            .filter(
                AssessmentAnswer.candidate_id == user_id,
                (AssessmentQuestion.canonical_skill_id == canonical_skill_id) | (AssessmentQuestion.skill.ilike(canonical_skill_id))
            )
            .all()
        )
        if len(skill_answers) >= 2:
            correct = sum(1 for a in skill_answers if a.is_correct)
            pct = (correct / len(skill_answers)) * 100.0
            if pct >= 75.0:
                return "Advanced"
            elif pct >= 50.0:
                return "Intermediate"
            else:
                return "Beginner"

        # 3. Fallback to StudentSkill score or claim status
        student_skill = (
            db.query(StudentSkill)
            .join(Skill, StudentSkill.skill_id == Skill.id)
            .filter(
                StudentSkill.user_id == user_id,
                (Skill.canonical_id == canonical_skill_id) | (Skill.name.ilike(canonical_skill_id))
            )
            .first()
        )
        if student_skill:
            if student_skill.assessment_score is not None:
                if student_skill.assessment_score >= 75.0:
                    return "Advanced"
                elif student_skill.assessment_score >= 50.0:
                    return "Intermediate"
                else:
                    return "Beginner"
            if student_skill.is_claimed:
                return "Intermediate"

        return "Beginner"

    @staticmethod
    def get_skill_topics(
        db: Session,
        user_id: int,
        canonical_skill_id: str,
        display_name: str
    ) -> List[TopicPerformanceItem]:
        """Dynamically discovers and aggregates topics and performance for any skill."""
        # 1. Fetch all assessment questions and answers for this user and skill
        history_records = (
            db.query(
                AssessmentQuestion.topic,
                AssessmentQuestion.concept,
                AssessmentAnswer.is_correct,
                AssessmentAnswer.answered_at
            )
            .join(AssessmentAnswer, AssessmentQuestion.id == AssessmentAnswer.question_id)
            .filter(
                AssessmentAnswer.candidate_id == user_id,
                (AssessmentQuestion.canonical_skill_id == canonical_skill_id) |
                (AssessmentQuestion.skill.ilike(display_name)) |
                (AssessmentQuestion.skill.ilike(canonical_skill_id))
            )
            .order_by(AssessmentAnswer.answered_at.desc())
            .all()
        )

        topic_stats: Dict[str, Dict[str, Any]] = {}

        for rec in history_records:
            t = (rec.topic or "Core Concepts").strip()
            if t.lower() in ("general", "core concept", "none"):
                t = "Core Concepts"

            if t not in topic_stats:
                topic_stats[t] = {
                    "attempted": 0,
                    "correct": 0,
                    "weak_concepts": set(),
                    "last_practiced": rec.answered_at
                }

            topic_stats[t]["attempted"] += 1
            if rec.is_correct:
                topic_stats[t]["correct"] += 1
            else:
                if rec.concept and rec.concept.strip().lower() not in ("core concept", "general", "none"):
                    topic_stats[t]["weak_concepts"].add(rec.concept.strip())

        # 2. Check active 7-Day Learning Plan activities for this skill
        plan_activities = (
            db.query(LearningActivity)
            .join(LearningPlan, LearningActivity.plan_id == LearningPlan.id)
            .filter(
                LearningPlan.user_id == user_id,
                LearningPlan.status == "active",
                (LearningActivity.skill_name.ilike(display_name) | LearningActivity.skill_name.ilike(canonical_skill_id))
            )
            .all()
        )
        for act in plan_activities:
            t = act.topic.strip()
            if t and t not in topic_stats:
                topic_stats[t] = {
                    "attempted": 0,
                    "correct": 0,
                    "weak_concepts": set(),
                    "last_practiced": None
                }

        # 3. If no topics yet tracked, populate with standard canonical starter topics
        if not topic_stats:
            is_edu = any(w in display_name.lower() for w in ["degree", "bachelor", "master", "mba", "phd", "diploma"])
            if is_edu:
                starter = [
                    f"{display_name} Curriculum & Specializations",
                    f"{display_name} Projects & Case Studies",
                    f"{display_name} Placement & Interview Preparation"
                ]
            else:
                starter = STARTER_TOPICS_MAP.get(canonical_skill_id) or [
                    f"{display_name} Fundamentals & Architecture",
                    f"{display_name} Best Practices & Design Patterns",
                    f"{display_name} Performance Optimization",
                    f"{display_name} Debugging & Error Handling",
                    f"{display_name} Security & Production Readiness"
                ]
            for t in starter:
                topic_stats[t] = {
                    "attempted": 0,
                    "correct": 0,
                    "weak_concepts": set(),
                    "last_practiced": None
                }

        # 4. Construct sorted TopicPerformanceItem list
        items: List[TopicPerformanceItem] = []
        for t_name, data in topic_stats.items():
            att = data["attempted"]
            corr = data["correct"]
            acc = round((corr / att) * 100.0, 1) if att > 0 else None

            if att == 0:
                status_val = "Unattempted"
            elif acc is not None and acc >= 80.0 and att >= 2:
                status_val = "Mastered"
            elif acc is not None and acc >= 60.0:
                status_val = "In Progress"
            else:
                status_val = "Needs Practice"

            items.append(TopicPerformanceItem(
                topic=t_name,
                skill_name=display_name,
                canonical_skill_id=canonical_skill_id,
                questions_attempted=att,
                correct_count=corr,
                accuracy_percentage=acc,
                status=status_val,
                weak_concepts=sorted(list(data["weak_concepts"])),
                last_practiced_at=data["last_practiced"]
            ))

        # Sort order: Needs Practice first, In Progress second, Unattempted third, Mastered last
        status_priority = {"Needs Practice": 1, "In Progress": 2, "Unattempted": 3, "Mastered": 4}
        items.sort(key=lambda x: (status_priority.get(x.status, 5), -(x.accuracy_percentage or 0.0)))
        return items

    @staticmethod
    def get_skill_focus_detail(
        db: Session,
        user_id: int,
        skill_identifier: str
    ) -> SkillFocusDetailResponse:
        """Assembles comprehensive focus details for any skill."""
        canon = canonicalize_skill(skill_identifier)

        # 1. Fetch StudentSkill record
        student_skill = (
            db.query(StudentSkill)
            .join(Skill, StudentSkill.skill_id == Skill.id)
            .filter(
                StudentSkill.user_id == user_id,
                (Skill.canonical_id == canon.canonical_id) | (Skill.name.ilike(canon.display_name))
            )
            .first()
        )

        current_score = student_skill.assessment_score if student_skill else None
        demonstrated = student_skill.demonstrated_level if student_skill else "Unassessed"
        confidence = student_skill.confidence if student_skill else "None"
        category = canon.category

        # 2. Determine JD Importance
        from backend.app.services.job_service import JobService
        latest_jd = JobService.get_active_target_job(db, user_id)
        jd_importance = "Bonus"
        if latest_jd and latest_jd.parsed_data:
            req_names = [r.get("name", "").lower() for r in latest_jd.parsed_data.get("required_skills", [])]
            pref_names = [p.get("name", "").lower() for p in latest_jd.parsed_data.get("preferred_skills", [])]
            name_lower = canon.display_name.lower()
            canon_lower = canon.canonical_id.lower()

            if any(name_lower == r or canon_lower in r or r in canon_lower for r in req_names):
                jd_importance = "Required" if (student_skill and student_skill.is_claimed) else "Missing"
            elif any(name_lower == p or canon_lower in p or p in canon_lower for p in pref_names):
                jd_importance = "Preferred"

        # 3. Dynamic Topics & Accuracy
        topics = SkillTopicService.get_skill_topics(db, user_id, canon.canonical_id, canon.display_name)

        # Count practice attempts
        practice_count = (
            db.query(Assessment)
            .filter(
                Assessment.candidate_id == user_id,
                Assessment.assessment_mode.in_(["practice", "focused_assessment"]),
                (Assessment.canonical_skill_id == canon.canonical_id) | (Assessment.role.ilike(canon.display_name))
            )
            .count()
        )

        # 4. Determine Dynamic Recommended Next Action
        needs_practice_topics = [t for t in topics if t.status == "Needs Practice"]
        unattempted_topics = [t for t in topics if t.status == "Unattempted"]
        mastered_topics = [t for t in topics if t.status == "Mastered"]

        if needs_practice_topics:
            top_t = needs_practice_topics[0]
            action = {
                "action_type": "PRACTICE",
                "skill": canon.display_name,
                "topic": top_t.topic,
                "title": f"Practice {top_t.topic}",
                "reason": f"Topic accuracy is currently {top_t.accuracy_percentage or 0}% ({len(top_t.weak_concepts)} weak concepts flagged).",
                "recommended_mode": "practice",
                "weak_concepts": top_t.weak_concepts
            }
        elif unattempted_topics and jd_importance in ("Required", "Missing"):
            top_t = unattempted_topics[0]
            action = {
                "action_type": "PRACTICE",
                "skill": canon.display_name,
                "topic": top_t.topic,
                "title": f"Practice {top_t.topic}",
                "reason": f"Required competency for your target role. No practice sessions logged yet.",
                "recommended_mode": "practice",
                "weak_concepts": []
            }
        elif len(mastered_topics) >= 2 or (current_score is not None and current_score >= 80.0):
            action = {
                "action_type": "FOCUSED_ASSESSMENT",
                "skill": canon.display_name,
                "topic": None,
                "title": f"Take Focused Assessment on {canon.display_name}",
                "reason": f"Demonstrated high topic mastery. Prove proficiency with a comprehensive 10-question evaluation.",
                "recommended_mode": "focused_assessment",
                "weak_concepts": []
            }
        else:
            first_topic = topics[0].topic if topics else None
            action = {
                "action_type": "PRACTICE",
                "skill": canon.display_name,
                "topic": first_topic,
                "title": f"Practice {canon.display_name}",
                "reason": f"Sharpen technical depth in {first_topic or canon.display_name}.",
                "recommended_mode": "practice",
                "weak_concepts": []
            }

        return SkillFocusDetailResponse(
            skill_name=canon.display_name,
            canonical_id=canon.canonical_id,
            category=category,
            jd_importance=jd_importance,
            current_score=current_score,
            demonstrated_level=demonstrated,
            confidence=confidence,
            total_practice_attempts=practice_count,
            topics=topics,
            recommended_action=action
        )
